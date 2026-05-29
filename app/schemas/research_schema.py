from pydantic import BaseModel

# document
class DocumentSchema(BaseModel):
    title: str
    url: str
    content: str
    distance: float

# response
class ResearchResponseSchema(BaseModel):
    query: str
    documents: list[DocumentSchema]
    provider: str
    
# request
class ResearchRequestSchema(BaseModel):
    query: str
    provider: str = "ddgs"

class RetrievedDocumentSchema(BaseModel):
    title: str
    url: str
    content: str