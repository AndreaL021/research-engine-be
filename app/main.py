from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware

from app.api.research import router as research_router

# database
from app.database.database import engine, Base
from app.models.document_model import DocumentModel
from app.models.query_document_model import QueryDocumentModel
from app.models.query_model import QueryModel


app = FastAPI()

Base.metadata.create_all(bind=engine)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://research-engine-fe.onrender.com",
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