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
from app.services.persistance.embedding_service import get_embedding_model


app = FastAPI()

Base.metadata.create_all(bind=engine)

get_embedding_model()

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
