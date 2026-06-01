from app.services.retrieval.providers.ddgs_provider import (
    retrieve_web_documents as retrieve_ddgs_documents
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
from sqlalchemy import func, desc



# development
def retrieve_chunks(db: Session, query: str, retrieval_mode: str):
    if retrieval_mode == "lexical":
        return retrieve_lexical_chunks(
            db=db,
            query=query,
        )
    else:
        return retrieve_similar_chunks(
            db=db,
            query=query,
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
    
    return await retrieve_ddgs_documents(
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

    return [
        DocumentSchema(
            title=document.title,
            url=document.url,
            content=chunk.content,
            score=max(0.0, 1.0 - float(distance))
        )
        for document, chunk, distance in result
    ]


# lexical
def retrieve_lexical_chunks(
    db: Session,
    query: str,
    limit: int = MAX_CHUNK_RESPONSE
):
    search_query = func.plainto_tsquery("english", query)

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
        .order_by(
            desc(rank)
        )
        .limit(limit)
        .all()
    )

    return [
        DocumentSchema(
            title=document.title,
            url=document.url,
            content=chunk.content,
            score=float(score)
        )
        for document, chunk, score in result
    ]