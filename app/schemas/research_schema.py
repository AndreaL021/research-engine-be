from pydantic import BaseModel

# document
class DocumentSchema(BaseModel):
    title: str
    url: str
    content: str
    score: float
    provider: str
    source_type: str
    content_type: str
    source_reliability: int
    search_engine: str | None = None
    search_category: str | None = None
    published_at: str | None = None
    search_score: int | None = None

# response
class ResearchResponseSchema(BaseModel):
    query: str
    documents: list[DocumentSchema]
    provider: str
    retrieval_mode: str
    
# request
class ResearchRequestSchema(BaseModel):
    query: str
    provider: str = "searxng"
    retrieval_mode: str = "semantic"

class RetrievedDocumentSchema(BaseModel):
    title: str
    url: str
    content: str
    engine: str | None = None
    category: str | None = None
    published_at: str | None = None
    search_score: float | None = None
