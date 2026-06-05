import httpx

from app.config.retrieval_config import EXA_API_KEY, MAX_CACHED_DOCUMENTS

from app.schemas.research_schema import RetrievedDocumentSchema
from app.services.retrieval.local.retrieval_utils import (
    clean_content,
    is_blocked_domain
)
from urllib.parse import urlparse


async def retrieve_web_documents(
    query: str,
    cached_length: int
):

    async with httpx.AsyncClient() as client:

        response = await client.post(
            "https://api.exa.ai/search",
            headers={
                "x-api-key": EXA_API_KEY,
                "Content-Type": "application/json",
            },
            json={
                "query": query,
                "numResults": MAX_CACHED_DOCUMENTS,
                "contents": {
                    "text": True
                }
            },
        )
        response.raise_for_status()

    data = response.json()

    documents = []

    for item in data.get("results", []):

        domain = urlparse(
            item.get("url", "")
        ).netloc.lower()
        
        if is_blocked_domain(domain):
            continue

        content = item.get("text", "")

        content = clean_content(content)

        if not content:
            continue

        documents.append(
            RetrievedDocumentSchema(
                title=item.get("title", ""),
                url=item.get("url", ""),
                content=content
            )
        )


    return documents
