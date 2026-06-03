# database
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
# models
from app.models.chunk_model import ChunkModel
from app.models.embedding_model import EmbeddingModel
# services persistance
from app.services.persistance.document_service import ( 
    get_document_by_url, 
    create_document, 
    get_cached_documents_count
)
from app.services.persistance.query_service import ( 
    get_query_by_text, 
    create_query
)
from app.services.persistance.query_document_service import (
    get_relation, 
    create_relation
)
from app.services.persistance.chunk_service import (
    create_chunks, 
    chunk_content
)
from app.services.persistance.embedding_service import (
    generate_embeddings, 
    create_embeddings
)
from app.services.persistance.entity_service import (
    create_chunk_entities,
)
# services retrieval
from app.services.retrieval.retrieval_service import (
    classify_source_type,
    calculate_source_reliability,
    detect_content_type,
    extract_publication_date,
    retrieve_web_documents,
    retrieve_chunks,
)
from app.services.llm.llm_service import generate_answer
# other
from urllib.parse import urlparse
from app.config.config import (MAX_CACHED_DOCUMENTS)
from fastapi import HTTPException
from app.services.tracking_service import PipelineTracker


async def retrieve_documents(query: str, provider: str, retrieval_mode: str):

    # create database session
    db: Session = SessionLocal()
    chunk_models = []
    tracker = PipelineTracker(
        query=query,
        provider=provider,
        retrieval_mode=retrieval_mode,
    )

    try:
        # return cached knowledge if query was already processed
        with tracker.measure("cache_lookup"):
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

        # retrieve existing query or create a new one
        with tracker.measure("query_lookup"):
            existing_query = get_query_by_text(
                db = db,
                query = query,
            )

        if existing_query:
        
            query_model = existing_query

        else:
        
            with tracker.measure("query_save"):
                query_model = create_query(
                    db = db,
                    query = query,
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

                # check if document already exists
                existing_document = get_document_by_url(
                    db = db,
                    url = document.url
                )

                # skip duplicate documents and only create
                # missing query-document relations
                if existing_document:
                    existing_relation = get_relation(
                        db = db,
                        id_query = query_model.id,
                        id_document = existing_document.id,
                    )

                    if not existing_relation:
                        
                        create_relation(
                            db = db,
                            id_query = query_model.id,
                            id_document = existing_document.id,
                        )
                    continue

                content_length = len(document.content.split())

                domain = urlparse(document.url).netloc

                # Enrich source metadata before chunking so every returned chunk can
                # carry document-level provenance and reliability signals.
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

                # create document into PostgreSQL
                document_model = create_document(
                    db = db,
                    title = document.title,
                    url = document.url,
                    content_length = content_length,
                    domain = domain,
                    provider = provider,
                    source_type = source_type,
                    content_type = content_type,
                    source_reliability = source_reliability,
                    search_engine = document.engine,
                    search_category = document.category,
                    author = document.author,
                    categories = document.categories,
                    tags = document.tags,
                    published_at = published_at,
                    search_score = int(document.search_score * 100) if document.search_score is not None else None,
                )
                
                # split document content into chunks
                chunks = chunk_content(document.content)

                # collect chunks for bulk insertion
                chunk_models.extend(
                    [
                        ChunkModel(
                            id_document=document_model.id,
                            chunk_index=index,
                            content=chunk,
                        )
                        for index, chunk in enumerate(chunks)
                    ]            
                )


                existing_relation = get_relation(
                    db = db,
                    id_query = query_model.id,
                    id_document = document_model.id,
                )

                if not existing_relation:
                
                    create_relation(
                        db = db,
                        id_query = query_model.id,
                        id_document = document_model.id,
                    )
                    
        # If the provider only returned duplicates, reuse the existing knowledge
        # base instead of failing the request.
        if not chunk_models:
            with tracker.measure("commit"):
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
           
        with tracker.measure("chunk_save"):
            create_chunks(
                db=db,
                chunks=chunk_models
            ) 

        # Entities are extracted after chunks are flushed so relations can use
        # generated chunk ids.
        with tracker.measure("entity_extraction"):
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
        
        with tracker.measure("embedding_save"):
            create_embeddings(
                db=db,
                embeddings=embedding_models
            )
        
        # commit transaction
        with tracker.measure("commit"):
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
    tracker.log(
        {
            "result_documents": len(documents),
        }
    )

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
