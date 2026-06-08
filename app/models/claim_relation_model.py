from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint

from app.database.database import Base


class ClaimRelationModel(Base):

    __tablename__ = "claim_relations"
    __table_args__ = (
        UniqueConstraint(
            "id_claim_a",
            "id_claim_b",
            name="unique_claim_relation",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    id_claim_a = Column(
        Integer,
        ForeignKey("claims.id"),
        nullable=False,
        index=True,
    )

    id_claim_b = Column(
        Integer,
        ForeignKey("claims.id"),
        nullable=False,
        index=True,
    )

    relation_type = Column(String, nullable=False, index=True)

    confidence = Column(Integer, nullable=False, default=50)

    explanation = Column(Text, nullable=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
