from sqlalchemy.orm import Session

from app.models.chunk_model import ChunkModel

from app.config.config import (
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)


def chunk_content(
    content: str,
    chunk_size: int = CHUNK_SIZE,
    overlap: int = CHUNK_OVERLAP,
) -> list[str]:
    words = content.split()

    chunks: list[str] = []

    step = chunk_size - overlap

    for start in range(0, len(words), step):

        end = start + chunk_size

        chunk_words = words[start:end]

        if not chunk_words:
            continue

        chunk = " ".join(chunk_words)

        chunks.append(chunk)

    return chunks


def create_chunks(
    db: Session,
    chunks: list[ChunkModel]
):
    db.add_all(chunks)

    db.flush()

    return chunks