from sqlalchemy.orm import Session

from app.models.query_model import QueryModel



def get_query_by_text(
    db: Session,
    query: str,
):

    # check if query already exists
    return db.query(QueryModel).filter(
        QueryModel.query == query
    ).first()



def create_query(
    db: Session,
    query: str,
):

    # create new query model
    query_model = QueryModel(
        query=query
    )

    # persist query into database
    db.add(query_model)

    # generate query id without commit
    db.flush()

    return query_model