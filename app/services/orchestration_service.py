# database
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
# services
from app.services.persistance.query_service import ( get_query_by_text, create_query)
from app.services.persistance.document_service import ( get_document_by_url, create_document, get_cached_documents_count)
from app.services.persistance.query_document_service import (get_relation, create_relation)
from app.services.retrieval.retrieval_service import (retrieve_web_documents, retrieve_similar_chunks)
from app.services.persistance.chunk_service import (create_chunks, chunk_content)
from app.services.persistance.embedding_service import (generate_embeddings, create_embeddings)
# models
from app.models.chunk_model import ChunkModel
from app.models.embedding_model import EmbeddingModel

from urllib.parse import urlparse

from app.config.config import (MAX_CACHED_DOCUMENTS)

from fastapi import HTTPException


async def retrieve_documents(query: str, provider:str):

    # create database session
    db: Session = SessionLocal()
    chunk_models = []

    try:
        # return cached knowledge if query was already processed
        cached_count = get_cached_documents_count(
            db = db,
            query = query,
        )
        
        # skip web retrieval and perform semantic retrieval directly
        if cached_count >= MAX_CACHED_DOCUMENTS:
            response = retrieve_similar_chunks(
                db=db,
                query=query,
            )
            return response

        # retrieve existing query or create a new one
        existing_query = get_query_by_text(
            db = db,
            query = query,
        )

        if existing_query:
        
            query_model = existing_query

        else:
        
            query_model = create_query(
                db = db,
                query = query,
            )

        # retrieve fresh documents from selected provider
        documents = await retrieve_web_documents(
            query = query,
            cached_length = cached_count,
            provider = provider
        )

    
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

            # create document into PostgreSQL
            document_model = create_document(
                db = db,
                title = document.title,
                url = document.url,
                content = document.content,
                content_length = content_length,
                domain = domain
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

        # no new knowledge was added
        if not chunk_models:
            db.commit()
            response = retrieve_similar_chunks(
                db=db,
                query=query,
            )
            return response  
           
        create_chunks(
            db=db,
            chunks=chunk_models
        ) 

        # generate embeddings for all new chunks
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
        response = retrieve_similar_chunks(
            db=db,
            query=query,
        )

    except Exception as error:

        # rollback failed transaction
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=str(error)
        )
    
    finally:

        # always close database session
        db.close()
        
    return response
