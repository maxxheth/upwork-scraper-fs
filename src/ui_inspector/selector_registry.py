"""Declarative registry of all selectors used by src/parser.py."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True)
class RegisteredSelector:
    """A registered selector contract from src/parser.py."""

    view: Literal["search_listings", "job_detail"]
    target_field: str
    css_selector: str
    description: str
    is_fragile: bool = False
    fragile_reason: str = ""
    auth_only: bool = False
    expected_type: Literal["text", "list", "number", "element"] = "text"
    sibling_child_tag: str | None = None  # If text lives in a sibling's child (e.g. icon container + sibling <strong>)
    join_with: str | None = None  # Join multi-element values (e.g. "$25 - $50")


CORE_PARSER_REGISTRY: list[RegisteredSelector] = [
    # --- Search Listings View (parse_job_listings) ---
    RegisteredSelector(
        view="search_listings",
        target_field="job_cards_container",
        css_selector="article.job-tile",
        description="Container element for each job card in search results",
        expected_type="element",
    ),
    RegisteredSelector(
        view="search_listings",
        target_field="title_and_url",
        css_selector="a[data-test*='job-tile-title-link']",
        description="Anchor tag holding job title and relative URL",
        expected_type="text",
    ),
    RegisteredSelector(
        view="search_listings",
        target_field="description",
        css_selector="[data-test*='JobDescription'] p",
        description="Snippet paragraph inside job description container",
        expected_type="text",
    ),
    RegisteredSelector(
        view="search_listings",
        target_field="hourly_rate",
        css_selector="[data-test='job-type-label'] strong",
        description="Hourly rate or budget label text",
        expected_type="text",
    ),
    RegisteredSelector(
        view="search_listings",
        target_field="experience_level",
        css_selector="[data-test='experience-level'] strong",
        description="Experience level (Intermediate, Expert, Entry level)",
        expected_type="text",
    ),
    RegisteredSelector(
        view="search_listings",
        target_field="duration",
        css_selector="[data-test='duration-label']",
        description="Estimated duration for hourly contracts",
        expected_type="text",
    ),
    RegisteredSelector(
        view="search_listings",
        target_field="skills",
        css_selector="[data-test='token'] span",
        description="Skill tags listed on the card",
        expected_type="list",
    ),
    RegisteredSelector(
        view="search_listings",
        target_field="posted",
        css_selector="[data-test='job-pubilshed-date'] span",
        description="Posted time (note UpWork's internal typo 'pubilshed')",
        is_fragile=True,
        fragile_reason="Relies on UpWork typo 'pubilshed'; breaks if corrected to 'published'",
        expected_type="text",
    ),

    # --- Job Detail Page (parse_job_detail) ---
    RegisteredSelector(
        view="job_detail",
        target_field="title",
        css_selector="h1",
        description="Job headline on detail page",
        expected_type="text",
    ),
    RegisteredSelector(
        view="job_detail",
        target_field="description",
        css_selector="[data-test='Description'] p.multiline-text",
        description="Full multiline job description",
        expected_type="text",
    ),
    RegisteredSelector(
        view="job_detail",
        target_field="posted",
        css_selector=".posted-on-line span",
        description="Detailed posted timestamp line",
        expected_type="text",
    ),
    RegisteredSelector(
        view="job_detail",
        target_field="hourly_rate",
        css_selector="[data-cy='clock-timelog']",
        description="Hourly rate icon container with sibling <strong>",
        expected_type="text",
        sibling_child_tag="strong",
        join_with=" - ",
    ),
    RegisteredSelector(
        view="job_detail",
        target_field="experience_level",
        css_selector="[data-cy='expertise']",
        description="Expertise level icon container with sibling <strong>",
        expected_type="text",
        sibling_child_tag="strong",
    ),
    RegisteredSelector(
        view="job_detail",
        target_field="duration",
        css_selector="[data-cy='duration2']",
        description="Duration icon container with sibling <strong>",
        expected_type="text",
        sibling_child_tag="strong",
    ),
    RegisteredSelector(
        view="job_detail",
        target_field="hours_per_week",
        css_selector="[data-cy='clock-hourly']",
        description="Hours per week icon container with sibling <strong>",
        expected_type="text",
        sibling_child_tag="strong",
    ),
    RegisteredSelector(
        view="job_detail",
        target_field="skills",
        css_selector="section[data-v-3b2c2248] .skills-list .air3-line-clamp",
        description="Skills list scoped to main detail section",
        is_fragile=True,
        fragile_reason="Hardcoded Vue scope hash data-v-3b2c2248 breaks whenever UpWork updates styles",
        expected_type="list",
    ),
    RegisteredSelector(
        view="job_detail",
        target_field="proposals",
        css_selector="li.ca-item span.title",
        description="Activity list item title containing 'Proposals'",
        expected_type="text",
    ),
    RegisteredSelector(
        view="job_detail",
        target_field="country",
        css_selector="li[data-qa='client-location']",
        description="Client country/location item",
        expected_type="text",
    ),
    RegisteredSelector(
        view="job_detail",
        target_field="client_spent",
        css_selector="[data-qa='client-spend']",
        description="Client total spent badge",
        expected_type="text",
    ),
    RegisteredSelector(
        view="job_detail",
        target_field="client_hires",
        css_selector="[data-qa='client-hires']",
        description="Client total hires badge",
        expected_type="text",
    ),
]
