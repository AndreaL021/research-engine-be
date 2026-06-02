from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, UniqueConstraint

from app.database.database import Base


class ChunkEntityModel(Base):

    __tablename__ = "chunk_entity"
    __table_args__ = (
        UniqueConstraint(
            "id_chunk",
            "id_entity",
            name="unique_chunk_entity",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    id_chunk = Column(Integer, ForeignKey("chunks.id"), nullable=False, index=True)

    id_entity = Column(Integer, ForeignKey("entities.id"), nullable=False, index=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
