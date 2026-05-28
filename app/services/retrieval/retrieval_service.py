from app.services.retrieval.providers.ddgs_provider import (
    retrieve_web_documents as retrieve_ddgs_documents
)

from app.services.retrieval.providers.google_provider import (
    retrieve_web_documents as retrieve_google_documents
)

from app.services.retrieval.providers.serpapi_provider import (
    retrieve_web_documents as retrieve_serpapi_documents
)


async def retrieve_web_documents(
    query: str,
    cached_length: int,
    provider: str,
):
    if provider == "google":

        return await retrieve_google_documents(
            query=query,
            cached_length=cached_length,
        )

    if provider == "serpapi":

        return await retrieve_serpapi_documents(
            query=query,
            cached_length=cached_length,
        )

    return await retrieve_ddgs_documents(
        query=query,
        cached_length=cached_length,
    )