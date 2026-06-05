# database
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
# models
from app.models.embedding_model import EmbeddingModel
# services ingestion
from app.services.ingestion.document_ingestion_service import (
    create_document_with_chunks,
)
# services persistance
from app.services.persistance.document_service import ( 
    get_document_by_url, 
    get_cached_documents_count
)
from app.services.persistance.query_service import ( 
    get_or_create_query,
)
from app.services.persistance.query_document_service import (
    ensure_query_document_relation,
)
from app.services.persistance.chunk_service import (
    create_chunks, 
)
from app.services.persistance.embedding_service import (
    generate_embeddings, 
    create_embeddings
)
from app.services.persistance.entity_service import (
    create_chunk_entities,
)
from app.services.persistance.claim_service import (
    create_claims,
)
# services retrieval
from app.services.retrieval.retrieval_service import (
    retrieve_web_documents,
    retrieve_chunks,
)
from app.services.llm.llm_service import generate_answer
# other
from app.config.retrieval_config import MAX_CACHED_DOCUMENTS
from fastapi import HTTPException
from app.services.utils.tracking_service import PipelineTracker


async def retrieve_documents(query: str, provider: str, retrieval_mode: str):

    # create database session
    db: Session = SessionLocal()
    chunk_models = []
    tracker = PipelineTracker(
        provider=provider,
        retrieval_mode=retrieval_mode,
    )

    try:
        # return cached knowledge if query was already processed
        cached_count = get_cached_documents_count(
            db = db,
            query = query,
        )
        
        # Once the query has enough linked sources, avoid repeated web calls that
        # usually return duplicates and go directly to local retrieval.
        if cached_count >= MAX_CACHED_DOCUMENTS:
            with tracker.measure("local_retrieval"):
                response = retrieve_chunks(
                    db=db,
                    query=query,
                    retrieval_mode=retrieval_mode,
                    tracker=tracker,
                )
            return create_research_result(
                query=query,
                documents=response,
                tracker=tracker,
            )

        query_model = get_or_create_query(
            db=db,
            query=query,
        )

        # retrieve fresh documents from selected provider
        with tracker.measure("web_retrieval"):
            documents = await retrieve_web_documents(
                query = query,
                cached_length = cached_count,
                provider = provider
            )

        with tracker.measure("document_processing"):
            for document in documents:

                existing_document = get_document_by_url(
                    db = db,
                    url = document.url
                )

                if existing_document:
                    ensure_query_document_relation(
                        db=db,
                        id_query=query_model.id,
                        id_document=existing_document.id,
                    )
                    continue

                document_model, new_chunks = create_document_with_chunks(
                    db=db,
                    document=document,
                    provider=provider,
                )

                chunk_models.extend(new_chunks)
                ensure_query_document_relation(
                    db=db,
                    id_query=query_model.id,
                    id_document=document_model.id,
                )
                    
        # If the provider only returned duplicates, reuse the existing knowledge
        # base instead of failing the request.
        if not chunk_models:
            db.commit()
            with tracker.measure("local_retrieval"):
                response = retrieve_chunks(
                    db=db,
                    query=query,
                    retrieval_mode=retrieval_mode,
                    tracker=tracker,
                )
            return create_research_result(
                query=query,
                documents=response,
                tracker=tracker,
            )
           
        create_chunks(
            db=db,
            chunks=chunk_models
        ) 

        # Claims are structured evidence units extracted from stored chunks.
        create_claims(
            db=db,
            chunks=chunk_models,
        )

        # Entities are extracted after chunks are flushed so relations can use
        # generated chunk ids.
        create_chunk_entities(
            db=db,
            chunks=chunk_models,
        )

        # generate embeddings for all new chunks
        with tracker.measure("embedding_generation"):
            vectors = generate_embeddings(
                [
                    chunk_model.content
                    for chunk_model in chunk_models
                ]
            )        
        
        embedding_models = [
            EmbeddingModel(
                id_chunk=chunk_model.id,
                vector=vectors[index]
            )
            for index, chunk_model in enumerate(chunk_models)
        ]
        
        create_embeddings(
            db=db,
            embeddings=embedding_models
        )
        
        # commit transaction
        db.commit()

        # perform semantic retrieval on the updated KB
        with tracker.measure("local_retrieval"):
            response = retrieve_chunks(
                db=db,
                query=query,
                retrieval_mode=retrieval_mode,
                tracker=tracker,
            )

    except Exception as error:

        # rollback failed transaction
        db.rollback()
        tracker.log(
            {
                "failed": 1,
                "error_type": type(error).__name__,
            }
        )
        tracker.finish()
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
    
    finally:

        # always close database session
        db.close()
        
    return create_research_result(
        query=query,
        documents=response,
        tracker=tracker,
    )


def create_research_result(
    query: str,
    documents: list,
    tracker: PipelineTracker,
):
    with tracker.measure("answer_generation"):
        answer = generate_answer(
            query=query,
            documents=documents,
        )

    tracker.finish()

    return {
        "documents": documents,
        "answer": answer,
    }
