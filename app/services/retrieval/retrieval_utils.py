from app.config.config import (
    BLOCKED_DOMAINS,
    MAX_CACHED_DOCUMENTS,
    MAX_RESULTS,
)


def is_blocked_domain(
    domain: str
):
    return any(
        domain.endswith(blocked_domain)
        for blocked_domain in BLOCKED_DOMAINS
    )

def clean_content(
    content: str
):
    content = " ".join(
        content.split()
    )

    return content[:10000]

def get_results_to_fetch(
    cached_length: int
):
    remaining_results = max(
        0,
        MAX_CACHED_DOCUMENTS - cached_length
    )

    return min(
        MAX_RESULTS,
        remaining_results
    )