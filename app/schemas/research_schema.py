from pydantic import BaseModel, Field

# retrieved chunk
class RetrievedChunkSchema(BaseModel):
    id_document: int | None = None
    id_chunk: int | None = None
    source_number: int | None = None
    chunk_index: int | None = None
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
    author: str | None = None
    categories: str | None = None
    tags: str | None = None
    published_at: str | None = None
    search_score: int | None = None

class EvidenceRelationSchema(BaseModel):
    relation_type: str
    confidence: int
    explanation: str | None = None
    claim_a: str
    claim_b: str


# response
class ResearchResponseSchema(BaseModel):
    query: str
    documents: list[RetrievedChunkSchema]
    provider: str
    retrieval_mode: str
    answer: str | None = None
    follow_up_questions: list[str] = Field(default_factory=list)
    evidence_relations: list[EvidenceRelationSchema] = Field(default_factory=list)
    
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
    author: str | None = None
    categories: str | None = None
    tags: str | None = None
    published_at: str | None = None
    search_score: float | None = None
