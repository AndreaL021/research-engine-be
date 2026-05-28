# database
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
# service
from app.services.persistence.query_service import ( get_query_by_text, create_query)
from app.services.persistence.document_service import ( get_document_by_url, create_document)
from app.services.persistence.relation_service import (get_relation, create_relation)
from app.services.retrieval.retrieval_service import retrieve_web_documents
from app.services.knowledge.knowledge_service import get_cached_documents_by_query

from urllib.parse import urlparse

from app.config.config import (MAX_CACHED_DOCUMENTS)


async def retrieve_documents(query: str):

    # create database session
    db: Session = SessionLocal()
    documents = []
    
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

        # retrieve fresh documents from external sources
        documents = await retrieve_web_documents(
            query = query
        )

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

        # commit transaction
        db.commit()
    except Exception as error:

        # rollback failed transaction
        db.rollback()

        print(error)

        return []

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

    return all_documents
