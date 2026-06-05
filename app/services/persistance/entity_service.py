import re
from collections import Counter

from sqlalchemy.orm import Session

from app.config.knowledge_config import ENTITY_STOPWORDS, MAX_ENTITIES_PER_CHUNK
from app.models.chunk_entity_model import ChunkEntityModel
from app.models.entity_model import EntityModel


def create_chunk_entities(
    db: Session,
    chunks,
):
    for chunk in chunks:
        entity_names = extract_entities(
            chunk.content
        )

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


def extract_entities(content: str):
    tokens = [
        token
        for token in re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{3,}\b", content.lower())
        if token not in ENTITY_STOPWORDS
    ]

    bigrams = [
        f"{tokens[index]} {tokens[index + 1]}"
        for index in range(len(tokens) - 1)
    ]

    candidates = tokens + bigrams

    counts = Counter(candidates)

    return [
        entity
        for entity, _ in counts.most_common(MAX_ENTITIES_PER_CHUNK)
    ]


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
