# database
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
# services
from app.services.persistence.query_service import ( get_query_by_text, create_query)
from app.services.persistence.document_service import ( get_document_by_url, create_document)
from app.services.persistence.relation_service import (get_relation, create_relation)
from app.services.retrieval.retrieval_service import retrieve_web_documents
from app.services.knowledge.knowledge_service import get_cached_documents_by_query
from app.services.persistence.chunk_service import (create_chunks, chunk_content)
from app.services.persistence.embedding_service import (generate_embeddings, create_embeddings)
# models
from app.models.chunk_model import ChunkModel
from app.models.embedding_model import EmbeddingModel

from urllib.parse import urlparse

from app.config.config import (MAX_CACHED_DOCUMENTS)

from fastapi import HTTPException
# debug
import time

async def retrieve_documents(query: str, provider:str):

    # create database session
    db: Session = SessionLocal()
    chunk_models = []

    try:
        # return cached knowledge if query was already processed
        cached_documents = get_cached_documents_by_query(
            db = db,
            query = query,
        )
        
        if len(cached_documents) >= MAX_CACHED_DOCUMENTS:
            return cached_documents

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
        start=time.time()
        # retrieve fresh documents from external sources
        documents = await retrieve_web_documents(
            query = query,
            cached_length = len(cached_documents),
            provider = provider
        )

        print(
            "RETRIEVAL:",
            round(time.time() - start, 2),
            "sec"
        )
        start_2=time.time()

        for document in documents:

            # check if document already exists
            existing_document = get_document_by_url(
                db = db,
                url = document.url
            )

            # create relation for existing document
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

            # persist document into PostgreSQL
            document_model = create_document(
                db = db,
                title = document.title,
                url = document.url,
                content = document.content,
                content_length = content_length,
                domain = domain
            )

            chunks = chunk_content(document.content)
        

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
              
        if not chunk_models:
            db.commit()
            return cached_documents     
           
        start_3=time.time()
        create_chunks(
            db=db,
            chunks=chunk_models
        )
        print(
            f"INSERT chunk:",
            round(time.time() - start_3, 2),
            "sec"
        )  
        
        start_emb=time.time()
        vectors = generate_embeddings(
            [
                chunk_model.content
                for chunk_model in chunk_models
            ]
        )
        print(
            f"generate embedding:",
            round(time.time() - start_emb, 2),
            "sec"
        )
        
        
        embedding_models = [
            EmbeddingModel(
                id_chunk=chunk_model.id,
                vector=vectors[index]
            )
            for index, chunk_model in enumerate(chunk_models)
        ]
        start_insert = time.time()
        create_embeddings(
            db=db,
            embeddings=embedding_models
        )
        print(
            f"INSERT embedding :",
            round(time.time() - start_insert, 2),
            "sec"
        )

        print(
            "TOTAL document PROCESSING:",
            round(time.time() - start_2, 2),
            "sec"
        )
        # commit transaction
        db.commit()
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
        
    cached_urls = {
        document.url
        for document in cached_documents
    }
    
    new_documents = [
        document
        for document in documents
        if document.url not in cached_urls
    ]
    
    all_documents = cached_documents + new_documents
    # for document in all_documents:
    #     chunks = chunk_content(document.content)
    #     print(len(chunks))

    return all_documents
