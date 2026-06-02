from sqlalchemy.orm import Session

from app.models.document_model import DocumentModel
from app.models.query_document_model import QueryDocumentModel
from app.models.query_model import QueryModel


def get_document_by_url(
    db: Session,
    url: str,
):

    # check if document already exists
    return db.query(DocumentModel).filter(
        DocumentModel.url == url
    ).first()


def create_document(
    db: Session,
    title: str,
    url: str,
    content_length:int,
    domain:str,
    provider: str,
    source_type: str,
    content_type: str,
    source_reliability: int,
    search_engine: str | None,
    search_category: str | None,
    published_at: str | None,
    search_score: int | None,
):

    # create new document model
    document_model = DocumentModel(
        title=title,
        url=url,
        content_length=content_length,
        domain=domain,
        provider=provider,
        source_type=source_type,
        content_type=content_type,
        source_reliability=source_reliability,
        search_engine=search_engine,
        search_category=search_category,
        published_at=published_at,
        search_score=search_score,
    )

    # persist document into database
    db.add(document_model)

    # generate document id without commit
    db.flush()

    return document_model


def get_cached_documents_count(
    db: Session,
    query: str,
):
    # retrieve cached query
    existing_query = db.query(QueryModel).filter(
        QueryModel.query == query
    ).first()

    # return empty cache if query does not exist
    if not existing_query:
        return 0
    
    return (
        db.query(QueryDocumentModel)
        .filter(
            QueryDocumentModel.id_query == existing_query.id
        )
        .count()
    )
