from sqlalchemy import Column, Integer, ForeignKey, DateTime

from datetime import datetime

from app.database.database import Base


class QueryDocumentModel(Base):

    __tablename__ = "query_document"

    id = Column(Integer, primary_key=True, index=True)

    id_query = Column(Integer, ForeignKey("queries.id"), nullable=False)
    
    id_document = Column(Integer, ForeignKey("documents.id"), nullable=False)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
