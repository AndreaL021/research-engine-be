from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.database.database import Base


class ClaimModel(Base):

    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)

    id_document = Column(
        Integer,
        ForeignKey("documents.id"),
        nullable=False,
        index=True,
    )

    id_chunk = Column(
        Integer,
        ForeignKey("chunks.id"),
        nullable=False,
        index=True,
    )

    claim_text = Column(Text, nullable=False)

    claim_type = Column(String, nullable=False, default="evidence", index=True)

    confidence = Column(Integer, nullable=False, default=50)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
