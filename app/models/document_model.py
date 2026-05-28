from sqlalchemy import Column, Integer, String, Text, DateTime

from datetime import datetime

from app.database.database import Base


class DocumentModel(Base):

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    title = Column(String, nullable=False)

    url = Column(String, unique=True, nullable=False, index=True)

    content = Column(Text, nullable=False)

    content_length = Column(Integer, nullable=False)

    domain = Column(String, nullable=False, index=True)
    
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)