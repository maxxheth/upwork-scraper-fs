#!/usr/bin/env bash
# ============================================================
# Provision WordPress Infrastructure on AWS (Terraform-like)
# ============================================================
# This script demonstrates infrastructure-as-code patterns
# for deploying the WordPress stack to AWS.
# Usage: ./provision.sh [plan|apply|destroy]
# ============================================================
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
STATE_FILE="${SCRIPT_DIR}/.provision-state.json"

AWS_REGION="${AWS_REGION:-us-east-1}"
ENVIRONMENT="${ENVIRONMENT:-staging}"
PROJECT_NAME="${PROJECT_NAME:-wp-crm-integration}"

echo "=== WP Infrastructure Provisioner ==="
echo "Environment: ${ENVIRONMENT}"
echo "Region: ${AWS_REGION}"
echo "Project: ${PROJECT_NAME}"
echo ""

plan() {
    echo "=== PLAN ==="
    echo "Resources to create:"
    echo "  - VPC with public/private subnets"
    echo "  - RDS MySQL 8.0 instance (db.t3.medium)"
    echo "  - ElastiCache Redis 7 cluster (cache.t3.micro)"
    echo "  - ECS Fargate cluster for WordPress"
    echo "  - Application Load Balancer"
    echo "  - CloudFront CDN distribution"
    echo "  - S3 bucket for media uploads"
    echo "  - IAM roles and policies"
    echo "  - CloudWatch alarms and dashboards"
    echo ""
    echo "Estimated monthly cost: ~$120-180"
}

apply() {
    echo "=== APPLY ==="
    echo "Step 1: Creating VPC..."
    # Simulated: aws ec2 create-vpc --cidr-block 10.0.0.0/16
    echo "  VPC created: vpc-${PROJECT_NAME}-${ENVIRONMENT}"

    echo "Step 2: Creating RDS MySQL instance..."
    # Simulated: aws rds create-db-instance --engine mysql --db-instance-class db.t3.medium
    echo "  RDS endpoint: ${PROJECT_NAME}-db.${AWS_REGION}.rds.amazonaws.com:3306"

    echo "Step 3: Creating ElastiCache Redis cluster..."
    echo "  Redis endpoint: ${PROJECT_NAME}-redis.${AWS_REGION}.cache.amazonaws.com:6379"

    echo "Step 4: Creating ECS Fargate service..."
    echo "  Task definition: ${PROJECT_NAME}-wp:1"
    echo "  Service: ${PROJECT_NAME}-wp-service"

    echo "Step 5: Creating ALB + CloudFront..."
    echo "  ALB DNS: ${PROJECT_NAME}-alb-${ENVIRONMENT}.${AWS_REGION}.elb.amazonaws.com"
    echo "  CloudFront ID: E${PROJECT_NAME}CF"

    echo "Step 6: Configuring monitoring..."
    echo "  CloudWatch dashboard: ${PROJECT_NAME}-${ENVIRONMENT}"
    echo "  Alarms: CPU > 80%, Memory > 85%, 5xx > 1%"

    # Save state
    cat > "${STATE_FILE}" <<EOF
{
  "project": "${PROJECT_NAME}",
  "environment": "${ENVIRONMENT}",
  "region": "${AWS_REGION}",
  "resources": {
    "vpc": "vpc-${PROJECT_NAME}-${ENVIRONMENT}",
    "rds": "${PROJECT_NAME}-db.${AWS_REGION}.rds.amazonaws.com",
    "redis": "${PROJECT_NAME}-redis.${AWS_REGION}.cache.amazonaws.com",
    "ecs": "${PROJECT_NAME}-wp-service",
    "alb": "${PROJECT_NAME}-alb-${ENVIRONMENT}.${AWS_REGION}.elb.amazonaws.com",
    "cloudfront": "E${PROJECT_NAME}CF"
  },
  "applied_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
}
EOF
    echo ""
    echo "State saved to ${STATE_FILE}"
    echo "✓ Infrastructure applied successfully"
}

destroy() {
    echo "=== DESTROY ==="
    if [ ! -f "${STATE_FILE}" ]; then
        echo "No state file found. Nothing to destroy."
        exit 0
    fi

    echo "Step 1: Draining ECS service..."
    echo "Step 2: Deleting RDS instance (with final snapshot)..."
    echo "Step 3: Deleting ElastiCache cluster..."
    echo "Step 4: Deleting ALB + CloudFront..."
    echo "Step 5: Deleting VPC..."

    rm -f "${STATE_FILE}"
    echo "✓ Infrastructure destroyed"
}

case "${1:-plan}" in
    plan) plan ;;
    apply) apply ;;
    destroy) destroy ;;
    *)
        echo "Usage: $0 [plan|apply|destroy]"
        exit 1
        ;;
esac
