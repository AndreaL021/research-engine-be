from sqlalchemy import (
    Column,
    Integer,
    Text,
    ForeignKey,
    DateTime
)

from datetime import datetime

from app.database.database import Base


class ChunkModel(Base):

    __tablename__ = "chunks"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    id_document = Column(
        Integer,
        ForeignKey("documents.id")
    )

    chunk_index = Column(
        Integer
    )

    content = Column(
        Text
    )

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)