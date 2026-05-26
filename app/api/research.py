from fastapi import APIRouter

from app.services.retrieval_service import retrieve_documents

router = APIRouter()


@router.post("/research")

async def research(payload: dict):

    query = payload.get("query")

    documents = await retrieve_documents(query)

    return {
        "query": query,
        "documents": documents,
    }