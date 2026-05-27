from sqlalchemy import Column, Integer, ForeignKey, DateTime
from sqlalchemy import UniqueConstraint

from datetime import datetime

from app.database.database import Base


class QueryDocumentModel(Base):

    __tablename__ = "query_document"
    __table_args__ = (
        UniqueConstraint(
            "id_query",
            "id_document",
            name="unique_query_document",
        ),
    )

    id = Column(Integer, primary_key=True, index=True)

    id_query = Column(Integer, ForeignKey("queries.id"), nullable=False, index=True)
    
    id_document = Column(Integer, ForeignKey("documents.id"), nullable=False, index=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
