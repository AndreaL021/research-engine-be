from sqlalchemy.orm import Session

from app.models.document_model import DocumentModel


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
    content: str,
    content_length:int,
    domain:str,
):

    # create new document model
    document_model = DocumentModel(
        title=title,
        url=url,
        content=content,
        content_length=content_length,
        domain=domain,
    )

    # persist document into database
    db.add(document_model)

    # generate document id without commit
    db.flush()

    return document_model