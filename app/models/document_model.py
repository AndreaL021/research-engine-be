from sqlalchemy import Column, Integer, String, Text

from app.database.database import Base


class DocumentModel(Base):

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)

    query = Column(String, nullable=False)

    title = Column(String, nullable=False)

    url = Column(String, nullable=False)

    content = Column(Text, nullable=False)