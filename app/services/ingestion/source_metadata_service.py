from datetime import date
import re
from urllib.parse import urlparse


def classify_source_type(
    url: str,
    category: str | None = None,
    engine: str | None = None,
):
    domain = urlparse(url).netloc.lower()
    metadata = f"{category or ''} {engine or ''}".lower()

    if any(keyword in metadata for keyword in {"arxiv", "pubmed", "semantic scholar", "science"}):
        return "academic"

    if "news" in metadata:
        return "news"

    if any(
        domain.endswith(academic_domain)
        for academic_domain in {
            "arxiv.org",
            "nature.com",
            "sciencedirect.com",
            "ncbi.nlm.nih.gov",
            "pubmed.ncbi.nlm.nih.gov",
            "springer.com",
            "ieee.org",
            "acm.org",
        }
    ):
        return "academic"

    if any(
        domain.endswith(documentation_domain)
        for documentation_domain in {
            "docs.python.org",
            "developer.mozilla.org",
            "docs.microsoft.com",
            "cloud.google.com",
            "docs.aws.amazon.com",
            "openai.com",
        }
    ):
        return "documentation"

    if any(
        domain.endswith(news_domain)
        for news_domain in {
            "bbc.com",
            "reuters.com",
            "apnews.com",
            "nytimes.com",
            "theguardian.com",
        }
    ):
        return "news"

    if any(
        domain.endswith(forum_domain)
        for forum_domain in {
            "reddit.com",
            "stackoverflow.com",
            "stackexchange.com",
            "quora.com",
        }
    ):
        return "forum"

    return "web"


def detect_content_type(
    url: str,
    title: str = "",
    category: str | None = None,
    engine: str | None = None,
):
    domain = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    metadata = f"{title} {category or ''} {engine or ''}".lower()

    if path.endswith(".pdf"):
        return "pdf"

    source_type = classify_source_type(url, category, engine)

    if source_type == "academic":
        return "paper"

    if source_type == "documentation":
        return "documentation"

    if source_type == "news":
        return "news"

    if source_type == "forum":
        return "forum"

    if "blog" in path or "blog" in metadata:
        return "blog"

    if "press" in path or "press release" in metadata:
        return "press_release"

    if domain.startswith("docs."):
        return "documentation"

    return "article"


def calculate_source_reliability(
    url: str,
    category: str | None = None,
    engine: str | None = None,
):
    source_type = classify_source_type(url, category, engine)

    if source_type == "academic":
        return 90

    if source_type == "documentation":
        return 85

    if source_type == "news":
        return 70

    if source_type == "forum":
        return 45

    return 55


def extract_publication_date(
    url: str,
    title: str = "",
    content: str = "",
    published_at: str | None = None,
):
    if published_at:
        return published_at

    text = f"{url} {title} {content[:1000]}"

    date_match = re.search(
        r"\b(20\d{2}|19\d{2})[-/](0?[1-9]|1[0-2])[-/](0?[1-9]|[12]\d|3[01])\b",
        text,
    )

    if date_match:
        year, month, day = date_match.groups()
        return date(
            int(year),
            int(month),
            int(day),
        ).isoformat()

    year_match = re.search(
        r"\b(20\d{2}|19\d{2})\b",
        text,
    )

    if year_match:
        return year_match.group(1)

    return None
