import re

from sqlalchemy import case, desc, func, or_
from sqlalchemy.orm import Session

from app.config.retrieval_config import (
    MAX_CHUNK_RESPONSE,
    MIN_LEXICAL_SCORE,
    MIN_SEMANTIC_SCORE,
)
from app.models.chunk_model import ChunkModel
from app.models.document_model import DocumentModel
from app.models.embedding_model import EmbeddingModel
from app.schemas.research_schema import RetrievedChunkSchema
from app.services.persistance.embedding_service import generate_embeddings


def retrieve_similar_chunks(
    db: Session,
    query: str,
    limit: int = MAX_CHUNK_RESPONSE,
):
    query_vector = generate_embeddings(
        [query]
    )[0]

    distance = EmbeddingModel.vector.cosine_distance(
        query_vector
    ).label("distance")

    result = (
        db.query(
            DocumentModel,
            ChunkModel,
            distance,
        )
        .join(
            EmbeddingModel,
            EmbeddingModel.id_chunk == ChunkModel.id,
        )
        .join(
            DocumentModel,
            DocumentModel.id == ChunkModel.id_document,
        )
        .order_by(
            distance
        )
        .limit(limit)
        .all()
    )

    documents = []

    for document, chunk, distance in result:
        score = max(0.0, 1.0 - float(distance))

        if score < MIN_SEMANTIC_SCORE:
            continue

        documents.append(
            build_document_schema(
                document=document,
                chunk=chunk,
                score=score,
            )
        )

    return documents


def retrieve_lexical_chunks(
    db: Session,
    query: str,
    limit: int = MAX_CHUNK_RESPONSE,
):
    search_query = func.websearch_to_tsquery("english", query)

    rank = func.ts_rank(
        func.to_tsvector("english", ChunkModel.content),
        search_query,
    ).label("score")

    result = (
        db.query(
            DocumentModel,
            ChunkModel,
            rank,
        )
        .join(
            DocumentModel,
            DocumentModel.id == ChunkModel.id_document,
        )
        .filter(
            func.to_tsvector("english", ChunkModel.content).op("@@")(search_query)
        )
        .filter(
            rank > MIN_LEXICAL_SCORE
        )
        .order_by(
            desc(rank)
        )
        .limit(limit)
        .all()
    )

    documents = [
        build_document_schema(
            document=document,
            chunk=chunk,
            score=float(score),
        )
        for document, chunk, score in result
    ]

    if documents:
        return documents

    # PostgreSQL full-text search can be strict for natural-language questions;
    # fallback to keyword overlap keeps lexical mode useful for sparse matches.
    return retrieve_keyword_chunks(
        db=db,
        query=query,
        limit=limit,
    )


def retrieve_keyword_chunks(
    db: Session,
    query: str,
    limit: int = MAX_CHUNK_RESPONSE,
):
    terms = extract_query_terms(query)

    if not terms:
        return []

    rank = sum(
        case(
            (ChunkModel.content.ilike(f"%{term}%"), 1),
            else_=0,
        )
        for term in terms
    ).label("score")

    result = (
        db.query(
            DocumentModel,
            ChunkModel,
            rank,
        )
        .join(
            DocumentModel,
            DocumentModel.id == ChunkModel.id_document,
        )
        .filter(
            or_(
                *[
                    ChunkModel.content.ilike(f"%{term}%")
                    for term in terms
                ]
            )
        )
        .order_by(
            desc(rank)
        )
        .limit(limit)
        .all()
    )

    max_score = max(
        [score for _, _, score in result],
        default=1,
    )

    return [
        build_document_schema(
            document=document,
            chunk=chunk,
            score=float(score) / max_score,
        )
        for document, chunk, score in result
        if score > 0
    ]


def extract_query_terms(query: str):
    stopwords = {
        "are",
        "can",
        "for",
        "how",
        "the",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
    }

    return [
        term
        for term in re.findall(r"\b[a-zA-Z0-9]{3,}\b", query.lower())
        if term not in stopwords
    ]


def build_document_schema(
    document: DocumentModel,
    chunk: ChunkModel,
    score: float,
):
    return RetrievedChunkSchema(
        id_document=document.id,
        id_chunk=chunk.id,
        chunk_index=chunk.chunk_index,
        title=document.title,
        url=document.url,
        content=chunk.content,
        score=score,
        provider=document.provider,
        source_type=document.source_type,
        content_type=document.content_type,
        source_reliability=document.source_reliability,
        search_engine=document.search_engine,
        search_category=document.search_category,
        author=document.author,
        categories=document.categories,
        tags=document.tags,
        published_at=document.published_at,
        search_score=document.search_score,
    )
