from ddgs import DDGS
import trafilatura
from app.schemas.research_schema import RetrievedDocumentSchema
from urllib.parse import urlparse
from ddgs.exceptions import DDGSException

from app.config.config import (
    MIN_CONTENT_WORDS, 
    TRUSTED_DOMAINS,
)

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
    # perform web retrieval through DDGS
    with DDGS() as ddgs:

        results_to_fetch = get_results_to_fetch(
            cached_length
        )
        
        try:
            results = ddgs.text(
                query,
                max_results=results_to_fetch,
                backend="duckduckgo"
            )
        except DDGSException:
            return documents

        seen_urls = set()

        for result in results:

            url = result.get("href")

            if not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)
            
            domain = urlparse(url).netloc.lower()

            if is_blocked_domain(domain):
                continue

            # download and extract webpage content
            downloaded = trafilatura.fetch_url(url)

            content = trafilatura.extract(downloaded)

            # fallback to DDGS snippet if extraction fails
            if not content:
                content = result.get("body")

            # skip empty content
            if not content:
                continue
            
            content = clean_content(content)

            # skip very short content
            if len(content.split()) < MIN_CONTENT_WORDS:
                continue

            # append response document
            documents.append(
                RetrievedDocumentSchema(
                    title=result.get("title"),
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
