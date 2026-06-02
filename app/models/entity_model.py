from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.database.database import Base


class EntityModel(Base):

    __tablename__ = "entities"

    id = Column(Integer, primary_key=True, index=True)

    name = Column(String, unique=True, nullable=False, index=True)

    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
