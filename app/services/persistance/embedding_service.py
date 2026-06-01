from functools import lru_cache

from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session

from app.config.config import EMBEDDING_MODEL
from app.models.embedding_model import (
    EmbeddingModel
)


@lru_cache(maxsize=1)
def get_embedding_model():
    return SentenceTransformer(EMBEDDING_MODEL)


def generate_embeddings(
    texts: list[str]
):
    model = get_embedding_model()

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
