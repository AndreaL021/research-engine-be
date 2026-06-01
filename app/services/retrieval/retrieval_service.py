from app.services.retrieval.providers.ddgs_provider import (
    retrieve_web_documents as retrieve_ddgs_documents
)

from app.services.retrieval.providers.searxng_provider import (
    retrieve_web_documents as retrieve_searxng_documents
)

from app.services.retrieval.providers.exa_provider import (
    retrieve_web_documents as retrieve_exa_documents
)

from app.services.retrieval.providers.tavily_provider import (
    retrieve_web_documents as retrieve_tavily_documents
)
from app.services.persistance.embedding_service import generate_embeddings
from sqlalchemy.orm import Session
from app.models.embedding_model import EmbeddingModel
from app.models.chunk_model import ChunkModel
from app.models.document_model import DocumentModel
from app.config.config import MAX_CHUNK_RESPONSE
from app.schemas.research_schema import DocumentSchema
from app.services.retrieval.reranking_service import rerank_chunks
from sqlalchemy import case, desc, func, or_
import re


MIN_SEMANTIC_SCORE = 0.2
MIN_LEXICAL_SCORE = 0.0
RERANKER_CANDIDATES = 10


# development
def retrieve_chunks(db: Session, query: str, retrieval_mode: str):
    if retrieval_mode == "lexical":
        documents = retrieve_lexical_chunks(
            db=db,
            query=query,
            limit=MAX_CHUNK_RESPONSE,
        )
    else:
        documents = retrieve_similar_chunks(
            db=db,
            query=query,
            limit=MAX_CHUNK_RESPONSE,
        )

    documents = sorted(
        documents,
        key=lambda document: document.score,
        reverse=True,
    )[:RERANKER_CANDIDATES]

    return rerank_chunks(
        query=query,
        documents=documents,
        limit=MAX_CHUNK_RESPONSE,
    )


# web
async def retrieve_web_documents(
    query: str,
    cached_length: int,
    provider: str,
):

    if provider == "tavily":

        return await retrieve_tavily_documents(
            query=query,
            cached_length=cached_length,
        )
    
    if provider == "exa":

        return await retrieve_exa_documents(
            query=query,
            cached_length=cached_length,
        )

    if provider == "ddgs":

        return await retrieve_ddgs_documents(
            query=query,
            cached_length=cached_length,
        )
    
    return await retrieve_searxng_documents(
        query=query,
        cached_length=cached_length,
    )


# semantic
def retrieve_similar_chunks(
    db: Session,
    query: str,
    limit: int = MAX_CHUNK_RESPONSE
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
            distance
        )
        .join(
            EmbeddingModel,
            EmbeddingModel.id_chunk == ChunkModel.id
        )
        .join(
            DocumentModel,
            DocumentModel.id == ChunkModel.id_document
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
            DocumentSchema(
                title=document.title,
                url=document.url,
                content=chunk.content,
                score=score
            )
        )

    return documents


# lexical
def retrieve_lexical_chunks(
    db: Session,
    query: str,
    limit: int = MAX_CHUNK_RESPONSE
):
    search_query = func.websearch_to_tsquery("english", query)

    rank = func.ts_rank(
        func.to_tsvector("english", ChunkModel.content),
        search_query
    ).label("score")

    result = (
        db.query(
            DocumentModel,
            ChunkModel,
            rank
        )
        .join(
            DocumentModel,
            DocumentModel.id == ChunkModel.id_document
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
        DocumentSchema(
            title=document.title,
            url=document.url,
            content=chunk.content,
            score=float(score)
        )
        for document, chunk, score in result
    ]

    if documents:
        return documents

    return retrieve_keyword_chunks(
        db=db,
        query=query,
        limit=limit,
    )


def retrieve_keyword_chunks(
    db: Session,
    query: str,
    limit: int = MAX_CHUNK_RESPONSE
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
            rank
        )
        .join(
            DocumentModel,
            DocumentModel.id == ChunkModel.id_document
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
        DocumentSchema(
            title=document.title,
            url=document.url,
            content=chunk.content,
            score=float(score) / max_score
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
