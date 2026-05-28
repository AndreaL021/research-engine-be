from app.services.retrieval.providers.ddgs_provider import (
    retrieve_web_documents as retrieve_ddgs_documents
)

from app.services.retrieval.providers.exa_provider import (
    retrieve_web_documents as retrieve_exa_documents
)

from app.services.retrieval.providers.tavily_provider import (
    retrieve_web_documents as retrieve_tavily_documents
)

async def retrieve_web_documents(
    query: str,
    cached_length: int,
    provider: str,
):

    if provider == "tavily":

        return await retrieve_tavily_documents(
            query=query,
            cached_length=cached_length,
        )
    
    if provider == "exa":

        return await retrieve_exa_documents(
            query=query,
            cached_length=cached_length,
        )
    
    return await retrieve_ddgs_documents(
        query=query,
        cached_length=cached_length,
    )