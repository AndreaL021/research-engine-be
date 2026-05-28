from ddgs import DDGS
import trafilatura
from app.schemas.research_schema import DocumentSchema
from urllib.parse import urlparse

from app.config.config import (
    BLOCKED_DOMAINS, 
    MAX_RESULTS, 
    MIN_CONTENT_WORDS, 
    TRUSTED_DOMAINS
)


async def retrieve_web_documents(
    query: str
):

    documents: list[DocumentSchema] = []

    # perform web retrieval through DDGS
    with DDGS() as ddgs:

        results = ddgs.text(query, max_results=MAX_RESULTS)
        seen_urls = set()
        
        for result in results:

            url = result.get("href")

            if not url:
                continue

            if url in seen_urls:
                continue

            seen_urls.add(url)
            
            domain = urlparse(url).netloc

            if domain in BLOCKED_DOMAINS:
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
            
            content = content.strip()

            # skip very short content
            if len(content.split()) < MIN_CONTENT_WORDS:
                continue

            # append response document
            documents.append(
                DocumentSchema(
                    title=result.get("title"),
                    url=url,
                    content=content,
                )
            )

        documents.sort(
            key=rank_document
        )

    return documents


def rank_document(document: DocumentSchema):

    domain = urlparse(document.url).netloc

    is_untrusted = domain not in TRUSTED_DOMAINS

    content_length = len(document.content.split())

    return (
        is_untrusted,
        -content_length,
    )
