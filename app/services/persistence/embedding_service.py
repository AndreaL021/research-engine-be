from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.models.embedding_model import (
    EmbeddingModel
)


model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")


def generate_embeddings(
    texts: list[str]
):
    return model.encode(
        texts
    ).tolist()


def create_embeddings(
    db: Session,
    embeddings: list[EmbeddingModel]
):
    db.add_all(embeddings)
    db.flush()
    return embeddings
