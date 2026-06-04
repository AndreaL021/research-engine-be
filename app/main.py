from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.api.research import router as research_router

# database
from app.database.database import engine, Base
from app.models.document_model import DocumentModel
from app.models.query_document_model import QueryDocumentModel
from app.models.query_model import QueryModel
from app.models.chunk_model import ChunkModel
from app.models.embedding_model import EmbeddingModel
from app.models.entity_model import EntityModel
from app.models.chunk_entity_model import ChunkEntityModel
from app.models.claim_model import ClaimModel
from app.services.model_preload_service import preload_models


app = FastAPI()

Base.metadata.create_all(bind=engine)

preload_models()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(research_router)


@app.get("/")
async def root():
    return {
        "message": "Research Engine API running"
    }
