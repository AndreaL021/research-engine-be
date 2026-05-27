from ddgs import DDGS
import trafilatura
from app.schemas.research_schema import DocumentSchema

# database
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.document_model import DocumentModel


async def retrieve_documents(query: str):

    documents: list[DocumentSchema] = []

    # create database session
    db: Session = SessionLocal()

    # check if documents already exist in database
    cached_documents = db.query(DocumentModel).filter(
        DocumentModel.query == query
    ).all()
    
    # return cached documents if available
    if cached_documents:
        return [
            DocumentSchema(
                title=document.title,
                url=document.url,
                content=document.content,
            )
            for document in cached_documents
        ]

    try:
        # web retrieval through DDGS
        with DDGS() as ddgs:

            results = ddgs.text(query, max_results=5)

            for result in results:

                url = result.get("href")

                if not url:
                    continue

                # download and extract webpage content
                downloaded = trafilatura.fetch_url(url)

                content = trafilatura.extract(downloaded)

                # fallback to DDGS snippet if extraction fails
                if not content:
                    content = result.get("body")

                # append response document
                documents.append(
                    DocumentSchema(
                        title= result.get("title"),
                        url= url,
                        content= content
                    )
                )

                # persist document into PostgreSQL
                document_model = DocumentModel(
                    query=query,
                    title=result.get("title"),
                    url=url,
                    content=content,
                )

                db.add(document_model)
                
            # commit transaction
            db.commit()
    except Exception as error:
        # rollback failed transaction
        db.rollback()
        print(error)

    finally:
        # always close database session
        db.close()

    return documents