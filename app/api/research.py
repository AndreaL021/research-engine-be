from fastapi import APIRouter

from app.services.orchestration_service import retrieve_documents

from app.schemas.research_schema import (
    ResearchRequestSchema,
    ResearchResponseSchema,
)

router = APIRouter()


@router.post("/research", response_model=ResearchResponseSchema)

async def research(payload: ResearchRequestSchema):

    documents = await retrieve_documents(payload.query, payload.provider)

    return {
        "query": payload.query,
        "provider": payload.provider,
        "documents": documents,
    }