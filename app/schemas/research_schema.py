from pydantic import BaseModel

# document
class DocumentSchema(BaseModel):
    title: str
    url: str
    content: str
    score: float

# response
class ResearchResponseSchema(BaseModel):
    query: str
    documents: list[DocumentSchema]
    provider: str
    retrieval_mode: str
    
# request
class ResearchRequestSchema(BaseModel):
    query: str
    provider: str = "ddgs"
    retrieval_mode: str = "semantic"

class RetrievedDocumentSchema(BaseModel):
    title: str
    url: str
    content: str