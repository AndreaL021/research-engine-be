from sqlalchemy import Column, ForeignKey, Integer, String, DateTime

from datetime import datetime

from app.database.database import Base


class QueryModel(Base):

    __tablename__ = "queries"

    id = Column(Integer, primary_key=True, index=True)

    query = Column(String, unique=True, nullable=False, index=True)

    query_type = Column(String, nullable=False, default="user", index=True)

    parent_query_id = Column(Integer, ForeignKey("queries.id"), nullable=True, index=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
