from sqlalchemy import (
    Column,
    Integer,
    ForeignKey,
    DateTime
)

from pgvector.sqlalchemy import Vector

from app.database.database import Base

from datetime import datetime

class EmbeddingModel(Base):

    __tablename__ = "embeddings"

    id = Column(
        Integer,
        primary_key=True,
        index=True
    )

    id_chunk = Column(
        Integer,
        ForeignKey("chunks.id"),
        unique=True,
    )

    vector = Column(
        Vector(384)
    )

    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow
    )