from pydantic import BaseModel

# document
class DocumentSchema(BaseModel):
    title: str
    url: str
    content: str

# response
class ResearchResponseSchema(BaseModel):
    query: str
    documents: list[DocumentSchema]
    
# request
class ResearchRequestSchema(BaseModel):
    query: str