from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.models.chunk_model import ChunkModel
from app.services.persistance.chunk_service import chunk_content
from app.services.persistance.document_service import create_document
from app.services.ingestion.source_metadata_service import (
    calculate_source_reliability,
    classify_source_type,
    detect_content_type,
    extract_publication_date,
)


def create_document_with_chunks(
    db: Session,
    document,
    provider: str,
):
    # Document-level metadata is stored once and reused by every returned chunk.
    source_type = classify_source_type(
        document.url,
        document.category,
        document.engine,
    )

    content_type = detect_content_type(
        document.url,
        document.title,
        document.category,
        document.engine,
    )

    source_reliability = calculate_source_reliability(
        document.url,
        document.category,
        document.engine,
    )

    published_at = extract_publication_date(
        url=document.url,
        title=document.title,
        content=document.content,
        published_at=document.published_at,
    )

    document_model = create_document(
        db=db,
        title=document.title,
        url=document.url,
        content_length=len(document.content.split()),
        domain=urlparse(document.url).netloc,
        provider=provider,
        source_type=source_type,
        content_type=content_type,
        source_reliability=source_reliability,
        search_engine=document.engine,
        search_category=document.category,
        author=document.author,
        categories=document.categories,
        tags=document.tags,
        published_at=published_at,
        search_score=int(document.search_score * 100) if document.search_score is not None else None,
    )

    chunks = [
        ChunkModel(
            id_document=document_model.id,
            chunk_index=index,
            content=chunk,
        )
        for index, chunk in enumerate(chunk_content(document.content))
    ]

    return document_model, chunks
