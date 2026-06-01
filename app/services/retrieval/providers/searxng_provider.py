import httpx
import trafilatura
from urllib.parse import urlparse

from app.config.config import (
    MIN_CONTENT_WORDS,
    SEARXNG_URL,
    TRUSTED_DOMAINS,
)
from app.schemas.research_schema import RetrievedDocumentSchema
from app.services.retrieval.retrieval_utils import (
    clean_content,
    get_results_to_fetch,
    is_blocked_domain,
)


async def retrieve_web_documents(
    query: str,
    cached_length: int
):
    documents: list[RetrievedDocumentSchema] = []

    results_to_fetch = get_results_to_fetch(
        cached_length
    )

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{SEARXNG_URL.rstrip('/')}/search",
                params={
                    "q": query,
                    "format": "json",
                    "categories": "general",
                },
            )
            response.raise_for_status()
    except httpx.HTTPError:
        return documents

    data = response.json()
    seen_urls = set()

    for result in data.get("results", [])[:results_to_fetch]:
        url = result.get("url")

        if not url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        domain = urlparse(url).netloc.lower()

        if is_blocked_domain(domain):
            continue

        downloaded = trafilatura.fetch_url(url)

        content = trafilatura.extract(downloaded)

        if not content:
            content = result.get("content")

        if not content:
            continue

        content = clean_content(content)

        if len(content.split()) < MIN_CONTENT_WORDS:
            continue

        documents.append(
            RetrievedDocumentSchema(
                title=result.get("title", ""),
                url=url,
                content=content,
            )
        )

    documents.sort(
        key=rank_document
    )

    return documents


def rank_document(document: RetrievedDocumentSchema):
    domain = urlparse(document.url).netloc.lower()

    is_untrusted = not any(
        domain.endswith(trusted_domain)
        for trusted_domain in TRUSTED_DOMAINS
    )

    content_length = len(document.content.split())

    return (
        is_untrusted,
        -content_length,
    )
