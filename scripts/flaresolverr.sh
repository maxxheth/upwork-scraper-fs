#!/usr/bin/env bash
# ==============================================================================
# flaresolverr.sh — Manage FlareSolverr Docker container lifecycle
#
# Commands:
#   start     Start the FlareSolverr container (creates if doesn't exist)
#   stop      Stop the running FlareSolverr container
#   restart   Restart the FlareSolverr container and wait for readiness
#   status    Check container status and readiness endpoint
#   logs      Tail/view container logs
#   rm        Stop and remove the container
#
# Environment / Override options (or configured in .env):
#   FLARESOLVERR_CONTAINER_NAME  (default: flaresolverr)
#   FLARESOLVERR_PORT            (default: 8193, or port from FLARESOLVERR_URL)
#   FLARESOLVERR_IMAGE           (default: ghcr.io/flaresolverr/flaresolverr:latest)
#   FLARESOLVERR_LOG_LEVEL       (default: info)
# ==============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

# Load .env if present
if [[ -f "${PROJECT_ROOT}/.env" ]]; then
    # Export only non-comment, non-empty lines
    set -a
    # shellcheck disable=SC1091
    source <(grep -E '^[A-Za-z_][A-Za-z0-9_]*=' "${PROJECT_ROOT}/.env")
    set +a
fi

# Determine default port from FLARESOLVERR_URL if defined, else 8193
DEFAULT_PORT="8193"
if [[ -n "${FLARESOLVERR_URL:-}" ]]; then
    EXTRACTED_PORT="$(echo "${FLARESOLVERR_URL}" | sed -e 's,^.*:,,' -e 's,/.*$,,' || true)"
    if [[ "${EXTRACTED_PORT}" =~ ^[0-9]+$ ]]; then
        DEFAULT_PORT="${EXTRACTED_PORT}"
    fi
fi

CONTAINER_NAME="${FLARESOLVERR_CONTAINER_NAME:-flaresolverr}"
PORT="${FLARESOLVERR_PORT:-${DEFAULT_PORT}}"
IMAGE="${FLARESOLVERR_IMAGE:-ghcr.io/flaresolverr/flaresolverr:latest}"
LOG_LEVEL="${FLARESOLVERR_LOG_LEVEL:-info}"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${BLUE}[INFO]${NC} $*"
}

log_success() {
    echo -e "${GREEN}[OK]${NC} $*"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $*"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $*" >&2
}

check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        log_error "Docker is not installed or not in PATH."
        exit 1
    fi

    if ! docker info >/dev/null 2>&1; then
        log_error "Docker daemon is not running or accessible. Please start Docker or check permissions."
        exit 1
    fi
}

container_exists() {
    docker container inspect "${CONTAINER_NAME}" >/dev/null 2>&1
}

container_is_running() {
    local running
    running="$(docker container inspect -f '{{.State.Running}}' "${CONTAINER_NAME}" 2>/dev/null || echo "false")"
    [[ "${running}" == "true" ]]
}

wait_for_ready() {
    local max_attempts=30
    local attempt=1
    local url="http://localhost:${PORT}/"

    log_info "Waiting for FlareSolverr to become ready at ${url}..."
    while [[ ${attempt} -le ${max_attempts} ]]; do
        if curl -s -f -m 3 "${url}" >/dev/null 2>&1; then
            log_success "FlareSolverr is ready at ${url}!"
            return 0
        fi
        sleep 1
        attempt=$((attempt + 1))
    done

    log_warn "FlareSolverr did not respond within ${max_attempts} seconds at ${url}."
    log_warn "Check container logs with: $0 logs"
    return 1
}

cmd_start() {
    check_docker

    if container_is_running; then
        log_info "Container '${CONTAINER_NAME}' is already running."
        wait_for_ready
        return 0
    fi

    if container_exists; then
        log_info "Starting existing container '${CONTAINER_NAME}'..."
        docker start "${CONTAINER_NAME}" >/dev/null
        log_success "Container '${CONTAINER_NAME}' started."
    else
        log_info "Creating and starting new container '${CONTAINER_NAME}' (Image: ${IMAGE}, Port: ${PORT}:8191)..."
        docker run -d \
            --name "${CONTAINER_NAME}" \
            -p "${PORT}:8191" \
            -e LOG_LEVEL="${LOG_LEVEL}" \
            --restart unless-stopped \
            "${IMAGE}" >/dev/null
        log_success "Container '${CONTAINER_NAME}' created and started."
    fi

    wait_for_ready
}

cmd_stop() {
    check_docker

    if ! container_exists; then
        log_info "Container '${CONTAINER_NAME}' does not exist."
        return 0
    fi

    if ! container_is_running; then
        log_info "Container '${CONTAINER_NAME}' is already stopped."
        return 0
    fi

    log_info "Stopping container '${CONTAINER_NAME}'..."
    docker stop "${CONTAINER_NAME}" >/dev/null
    log_success "Container '${CONTAINER_NAME}' stopped."
}

cmd_restart() {
    check_docker
    log_info "Restarting FlareSolverr..."
    cmd_stop
    cmd_start
}

cmd_status() {
    check_docker

    echo "=========================================================="
    echo " FlareSolverr Container Status"
    echo "=========================================================="
    echo " Container Name: ${CONTAINER_NAME}"
    echo " Target Image:   ${IMAGE}"
    echo " Expected Port:  ${PORT}"
    echo " Endpoint URL:   http://localhost:${PORT}/"
    echo "----------------------------------------------------------"

    if ! container_exists; then
        echo -e " State:          ${YELLOW}NOT CREATED${NC}"
        echo " Action:         Run '$0 start' to create and run it."
        return 0
    fi

    local status
    status="$(docker container inspect -f '{{.State.Status}}' "${CONTAINER_NAME}" 2>/dev/null || echo "unknown")"

    if container_is_running; then
        echo -e " State:          ${GREEN}RUNNING${NC} (${status})"

        # Check actual port bindings
        local bound_ports
        bound_ports="$(docker port "${CONTAINER_NAME}" 2>/dev/null || echo "none")"
        echo " Port Bindings:  ${bound_ports//$'\n'/; }"

        # Ping health endpoint
        local response
        if response="$(curl -s -m 3 "http://localhost:${PORT}/" 2>/dev/null)"; then
            echo -e " Endpoint Health: ${GREEN}OK${NC}"
            echo " Response:       ${response}"
        else
            echo -e " Endpoint Health: ${RED}FAILED${NC} (No response at http://localhost:${PORT}/)"
        fi
    else
        echo -e " State:          ${RED}STOPPED${NC} (${status})"
        echo " Action:         Run '$0 start' to start it."
    fi
}

cmd_logs() {
    check_docker

    if ! container_exists; then
        log_error "Container '${CONTAINER_NAME}' does not exist."
        return 1
    fi

    local follow_flag=""
    if [[ "${1:-}" == "-f" || "${1:-}" == "--follow" ]]; then
        follow_flag="-f"
        shift || true
    fi

    docker logs ${follow_flag} --tail "${1:-100}" "${CONTAINER_NAME}"
}

cmd_rm() {
    check_docker

    if ! container_exists; then
        log_info "Container '${CONTAINER_NAME}' does not exist."
        return 0
    fi

    if container_is_running; then
        log_info "Stopping container '${CONTAINER_NAME}'..."
        docker stop "${CONTAINER_NAME}" >/dev/null
    fi

    log_info "Removing container '${CONTAINER_NAME}'..."
    docker rm "${CONTAINER_NAME}" >/dev/null
    log_success "Container '${CONTAINER_NAME}' removed."
}

show_help() {
    cat <<EOF
Usage: $0 {start|stop|restart|status|logs|rm}

Manage the FlareSolverr Docker container for the UpWork scraper.

Commands:
  start       Start FlareSolverr (creates container if not already existing)
  stop        Stop the FlareSolverr container
  restart     Restart the FlareSolverr container and wait for readiness
  status      Display container state and test endpoint health
  logs [-f]   View container logs (optional -f / --follow to tail)
  rm          Stop and remove the container

Configuration:
  Port, container name, and image can be customized via .env or environment:
    FLARESOLVERR_PORT=8193
    FLARESOLVERR_CONTAINER_NAME=flaresolverr
    FLARESOLVERR_IMAGE=ghcr.io/flaresolverr/flaresolverr:latest
    FLARESOLVERR_LOG_LEVEL=info

EOF
}

# Main command dispatch
case "${1:-}" in
    start|up)
        cmd_start
        ;;
    stop|down)
        cmd_stop
        ;;
    restart)
        cmd_restart
        ;;
    status)
        cmd_status
        ;;
    logs)
        shift
        cmd_logs "$@"
        ;;
    rm|clean)
        cmd_rm
        ;;
    help|--help|-h|"")
        show_help
        ;;
    *)
        log_error "Unknown command: $1"
        echo ""
        show_help
        exit 1
        ;;
esac
