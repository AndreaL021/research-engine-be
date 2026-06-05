from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.chunk_model import ChunkModel
from app.models.chunk_entity_model import ChunkEntityModel
from app.models.entity_model import EntityModel
from app.services.ingestion.entity_extraction_service import extract_entities
from app.services.utils.tracking_service import PipelineTracker


def create_chunk_entities(
    db: Session,
    chunks,
):
    for chunk in chunks:
        try:
            entity_names = extract_entities(chunk.content)
        except Exception:
            continue

        for entity_name in entity_names:
            entity = get_or_create_entity(
                db=db,
                name=entity_name,
            )

            create_chunk_entity_relation(
                db=db,
                id_chunk=chunk.id,
                id_entity=entity.id,
            )


def get_or_create_entity(
    db: Session,
    name: str,
):
    existing_entity = db.query(EntityModel).filter(
        EntityModel.name == name
    ).first()

    if existing_entity:
        return existing_entity

    entity = EntityModel(
        name=name
    )

    db.add(entity)
    db.flush()

    return entity


def create_chunk_entity_relation(
    db: Session,
    id_chunk: int,
    id_entity: int,
):
    existing_relation = db.query(ChunkEntityModel).filter(
        ChunkEntityModel.id_chunk == id_chunk,
        ChunkEntityModel.id_entity == id_entity,
    ).first()

    if existing_relation:
        return existing_relation

    relation = ChunkEntityModel(
        id_chunk=id_chunk,
        id_entity=id_entity,
    )

    db.add(relation)
    db.flush()

    return relation


def create_entities_for_chunk_ids(
    chunk_ids: list[int],
    provider: str,
    retrieval_mode: str,
):
    db: Session = SessionLocal()
    tracker = PipelineTracker(
        provider=f"{provider}-entities",
        retrieval_mode=retrieval_mode,
    )

    try:
        chunks = (
            db.query(ChunkModel)
            .filter(ChunkModel.id.in_(chunk_ids))
            .all()
        )

        with tracker.measure("entity_extraction"):
            create_chunk_entities(
                db=db,
                chunks=chunks,
            )

        db.commit()
    except Exception as error:
        db.rollback()
        tracker.log(
            {
                "failed": 1,
                "error_type": type(error).__name__,
            }
        )
    finally:
        tracker.finish()
        db.close()
