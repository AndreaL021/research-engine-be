from sqlalchemy import Column, Integer, String, DateTime

from datetime import datetime

from app.database.database import Base


class DocumentModel(Base):

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    url = Column(String, unique=True, nullable=False, index=True)

    content_length = Column(Integer, nullable=False)

    domain = Column(String, nullable=False, index=True)

    provider = Column(String, nullable=False, index=True)

    source_type = Column(String, nullable=False, default="unknown", index=True)

    content_type = Column(String, nullable=False, default="unknown", index=True)

    source_reliability = Column(Integer, nullable=False, default=50)

    search_engine = Column(String, nullable=True, index=True)

    search_category = Column(String, nullable=True, index=True)

    published_at = Column(String, nullable=True, index=True)

    search_score = Column(Integer, nullable=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
