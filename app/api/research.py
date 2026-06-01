from fastapi import APIRouter

from app.services.orchestration_service import retrieve_documents

from app.schemas.research_schema import (
    ResearchRequestSchema,
    ResearchResponseSchema,
)

router = APIRouter()


@router.post("/research", response_model=ResearchResponseSchema)

async def research(payload: ResearchRequestSchema):

    response = await retrieve_documents(
        payload.query, 
        payload.provider, 
        payload.retrieval_mode
    )

    return {
        "query": payload.query,
        "documents": response,
        "provider": payload.provider,
        "retrieval_mode": payload.retrieval_mode
    }