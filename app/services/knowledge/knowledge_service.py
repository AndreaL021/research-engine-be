from sqlalchemy.orm import Session

from app.schemas.research_schema import DocumentSchema

from app.models.query_document_model import QueryDocumentModel
from app.models.document_model import DocumentModel
from app.models.query_model import QueryModel

def get_cached_documents_by_query(
    db: Session,
    query: str,
):
    # retrieve cached query
    existing_query = db.query(QueryModel).filter(
        QueryModel.query == query
    ).first()

    # return empty cache if query does not exist
    if not existing_query:
        return []
    
    # retrieve query-document relations
    query_relations = db.query(QueryDocumentModel).filter(
        QueryDocumentModel.id_query == existing_query.id
    ).all()

    cached_documents: list[DocumentSchema] = []

    for relation in query_relations:

        document = db.query(DocumentModel).filter(
            DocumentModel.id == relation.id_document
        ).first()

        if not document:
            continue
        
        # build cached document response
        cached_documents.append(
            DocumentSchema(
                title=document.title,
                url=document.url,
                content=document.content,
            )
        )

    return cached_documents