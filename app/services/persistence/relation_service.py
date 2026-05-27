from sqlalchemy.orm import Session

from app.models.query_document_model import QueryDocumentModel


def create_relation(
    db: Session,
    id_query: int,
    id_document: int,
):

    # create new query-document relation
    query_document_model = QueryDocumentModel(
        id_query=id_query,
        id_document=id_document,
    )

    # persist relation into database
    db.add(query_document_model)

    return query_document_model


def get_relation(
    db: Session,
    id_query: int,
    id_document: int,
):

    # check if relation already exists
    return db.query(QueryDocumentModel).filter(
        QueryDocumentModel.id_query == id_query,
        QueryDocumentModel.id_document == id_document,
    ).first()