from app.config.config import (
    BLOCKED_DOMAINS,
    MAX_CACHED_DOCUMENTS,
    MAX_RESULTS,
)
import json
import re

import trafilatura

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
    # Remove common article/navigation boilerplate before chunking and embedding.
    content = re.sub(r"#{1,6}\s*", " ", content)

    content = re.sub(r"\b(RSS|Search|Subscribe|Share|Filed|Issue)\b", " ", content)

    content = re.sub(r"\b\d+\s+min read\b", " ", content, flags=re.IGNORECASE)

    content = re.sub(r"Paper\s*↗", " ", content)

    content = re.sub(r"\s+", " ", content)

    return content.strip()[:10000]

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


def extract_trafilatura_metadata(
    downloaded: str | None,
    url: str,
):
    if not downloaded:
        return {}

    extracted = trafilatura.extract(
        downloaded,
        url=url,
        output_format="json",
        with_metadata=True,
    )

    if not extracted:
        return {}

    try:
        data = json.loads(extracted)
    except json.JSONDecodeError:
        return {}

    return {
        "title": data.get("title"),
        "author": normalize_metadata_value(data.get("author")),
        "categories": normalize_metadata_value(data.get("categories")),
        "tags": normalize_metadata_value(data.get("tags")),
        "published_at": data.get("date"),
        "content": data.get("text"),
    }


def normalize_metadata_value(value):
    if not value:
        return None

    if isinstance(value, list):
        return ", ".join(
            [
                str(item)
                for item in value
                if item
            ]
        )

    return str(value)


