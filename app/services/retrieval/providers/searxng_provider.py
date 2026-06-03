import httpx
import trafilatura
from urllib.parse import urlparse

from app.config.config import (
    MAX_CACHED_DOCUMENTS,
    MIN_CONTENT_WORDS,
    SEARXNG_URL,
    TRUSTED_DOMAINS,
)
from app.schemas.research_schema import RetrievedDocumentSchema
from app.services.retrieval.retrieval_utils import (
    clean_content,
    extract_trafilatura_metadata,
    get_results_to_fetch,
    is_blocked_domain,
)


MAX_TRAFILATURA_DOWNLOADS = 5


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
    # Rank cheap SearXNG candidates first, then spend Trafilatura downloads only
    # on the most promising URLs.
    ranked_results = rank_search_results(
        data.get("results", [])
    )

    for result in ranked_results[:results_to_fetch]:
        url = result.get("url")

        if not url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        domain = urlparse(url).netloc.lower()

        if is_blocked_domain(domain):
            continue

        content = result.get("content")
        extracted_metadata = {}

        # SearXNG snippets are fast but shallow; Trafilatura is slower, so it is
        # limited to the best candidates and used to build richer chunks.
        if len(documents) < MAX_TRAFILATURA_DOWNLOADS:
            downloaded = trafilatura.fetch_url(url)

            extracted_metadata = extract_trafilatura_metadata(
                downloaded=downloaded,
                url=url,
            )

            if extracted_metadata.get("content"):
                content = extracted_metadata["content"]
            else:
                extracted_metadata = {}

        if not content:
            continue

        content = clean_content(content)

        if len(content.split()) < MIN_CONTENT_WORDS:
            continue

        documents.append(
            RetrievedDocumentSchema(
                title=result.get("title") or extracted_metadata.get("title") or "",
                url=url,
                content=content,
                engine=get_search_engine(result),
                category=result.get("category"),
                author=extracted_metadata.get("author"),
                categories=extracted_metadata.get("categories"),
                tags=extracted_metadata.get("tags"),
                published_at=result.get("publishedDate") or extracted_metadata.get("published_at"),
                search_score=parse_search_score(result.get("score")),
            )
        )

    documents.sort(
        key=rank_document
    )

    return documents


def rank_search_results(results: list[dict]):
    candidates = []
    seen_urls = set()

    # Inspect more search results than we plan to store, so duplicate/blocked
    # URLs do not exhaust the candidate pool too early.
    for result in results[:MAX_CACHED_DOCUMENTS * 2]:
        url = result.get("url")

        if not url:
            continue

        if url in seen_urls:
            continue

        seen_urls.add(url)

        domain = urlparse(url).netloc.lower()

        if is_blocked_domain(domain):
            continue

        candidates.append(result)

    candidates.sort(
        key=rank_search_result,
        reverse=True,
    )

    return candidates


def rank_search_result(result: dict):
    url = result.get("url", "")
    domain = urlparse(url).netloc.lower()
    content = result.get("content") or ""
    category = (result.get("category") or "").lower()
    engine = (get_search_engine(result) or "").lower()
    search_score = parse_search_score(result.get("score")) or 0

    # This score is only a pre-download heuristic. The final ranking still uses
    # chunk retrieval, metadata boosts, and the reranker.
    trusted_boost = 0.2 if any(
        domain.endswith(trusted_domain)
        for trusted_domain in TRUSTED_DOMAINS
    ) else 0

    academic_boost = 0.15 if any(
        keyword in f"{category} {engine} {domain}"
        for keyword in ("arxiv", "pubmed", "semantic scholar", "science", "academic")
    ) else 0

    snippet_boost = min(
        len(content.split()) / 80,
        0.2,
    )

    return search_score + trusted_boost + academic_boost + snippet_boost


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


def get_search_engine(result: dict):
    engines = result.get("engines")

    if isinstance(engines, list) and engines:
        return ", ".join(engines)

    return result.get("engine")


def parse_search_score(score):
    if score is None:
        return None

    try:
        return float(score)
    except (TypeError, ValueError):
        return None
