from ddgs import DDGS
import trafilatura
from app.schemas.research_schema import DocumentSchema

# database
from sqlalchemy.orm import Session
from app.database.database import SessionLocal
from app.models.document_model import DocumentModel
from app.models.query_model import QueryModel
from app.models.query_document_model import QueryDocumentModel


async def retrieve_documents(query: str):

    documents: list[DocumentSchema] = []

    # create database session
    db: Session = SessionLocal()


    try:
        # check if query already exists
        existing_query = db.query(QueryModel).filter(
            QueryModel.query == query
        ).first()
        if existing_query:

            # retrieve existing query-document relations
            query_documents = db.query(QueryDocumentModel).filter(
                QueryDocumentModel.id_query == existing_query.id
            ).all()

            if query_documents:
            
                # load cached documents from database
                cached_documents: list[DocumentSchema] = []

                for relation in query_documents:
                
                    document = db.query(DocumentModel).filter(
                        DocumentModel.id == relation.id_document
                    ).first()

                    if not document:
                        continue
                    
                    cached_documents.append(
                        DocumentSchema(
                            title=document.title,
                            url=document.url,
                            content=document.content,
                        )
                    )

                # return cached response if available
                if cached_documents:
                    return cached_documents
            query_model = existing_query
        else:
            # create new query entry
            query_model = QueryModel(
                query=query
            )
            db.add(query_model)

            # generate query id without commit
            db.flush()

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


                # check if document already exists
                existing_document = db.query(DocumentModel).filter(
                    DocumentModel.url == url
                ).first()

                # create relation only if document already exists
                if existing_document:
                    query_document_model = QueryDocumentModel(
                        id_query=query_model.id,
                        id_document=existing_document.id, 
                    )
                    # avoid duplicate query-document relation
                    existing_relation = db.query(QueryDocumentModel).filter(
                        QueryDocumentModel.id_query == query_model.id,
                        QueryDocumentModel.id_document == existing_document.id,
                    ).first()
                    if existing_relation:
                        continue
                    db.add(query_document_model)
                    continue

                # persist document into PostgreSQL
                document_model = DocumentModel(
                    title=result.get("title"),
                    url=url,
                    content=content,
                )

                db.add(document_model)
                # generate document id without commit
                db.flush()

                query_document_model = QueryDocumentModel(
                    id_query=query_model.id,
                    id_document=document_model.id,
                )
                
                # avoid duplicate query-document relation
                existing_relation = db.query(QueryDocumentModel).filter(
                    QueryDocumentModel.id_query == query_model.id,
                    QueryDocumentModel.id_document == document_model.id,
                ).first()
                if existing_relation:
                    continue

                db.add(query_document_model)

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