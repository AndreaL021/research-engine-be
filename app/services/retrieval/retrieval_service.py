from app.services.retrieval.providers.ddgs_provider import (
    retrieve_web_documents as retrieve_ddgs_documents
)

from app.services.retrieval.providers.searxng_provider import (
    retrieve_web_documents as retrieve_searxng_documents
)

from app.services.retrieval.providers.exa_provider import (
    retrieve_web_documents as retrieve_exa_documents
)

from app.services.retrieval.providers.tavily_provider import (
    retrieve_web_documents as retrieve_tavily_documents
)
from app.services.persistance.embedding_service import generate_embeddings
from sqlalchemy.orm import Session
from app.models.embedding_model import EmbeddingModel
from app.models.chunk_model import ChunkModel
from app.models.document_model import DocumentModel
from app.config.config import (
    MAX_CHUNK_RESPONSE,
    MIN_LEXICAL_SCORE,
    MIN_SEMANTIC_SCORE,
    RERANKER_CANDIDATES,
)
from app.schemas.research_schema import DocumentSchema
from app.services.retrieval.scoring_service import (
    apply_metadata_boost,
    rerank_chunks,
)
from sqlalchemy import case, desc, func, or_
from urllib.parse import urlparse
import re


# development
def retrieve_chunks(db: Session, query: str, retrieval_mode: str):
    if retrieval_mode == "lexical":
        documents = retrieve_lexical_chunks(
            db=db,
            query=query,
            limit=MAX_CHUNK_RESPONSE,
        )
    else:
        documents = retrieve_similar_chunks(
            db=db,
            query=query,
            limit=MAX_CHUNK_RESPONSE,
        )

    # Metadata boosts choose better reranker candidates without replacing the
    # actual semantic/lexical relevance score.
    boosted_documents = apply_metadata_boost(
        documents
    )

    sorted_documents = sorted(
        boosted_documents,
        key=lambda document: document.score,
        reverse=True,
    )

    documents = select_reranker_candidates(
        sorted_documents,
        limit=RERANKER_CANDIDATES,
    )

    return rerank_chunks(
        query=query,
        documents=documents,
        limit=MAX_CHUNK_RESPONSE,
    )


# web
async def retrieve_web_documents(
    query: str,
    cached_length: int,
    provider: str,
):

    if provider == "tavily":

        return await retrieve_tavily_documents(
            query=query,
            cached_length=cached_length,
        )
    
    if provider == "exa":

        return await retrieve_exa_documents(
            query=query,
            cached_length=cached_length,
        )

    if provider == "ddgs":

        return await retrieve_ddgs_documents(
            query=query,
            cached_length=cached_length,
        )
    
    return await retrieve_searxng_documents(
        query=query,
        cached_length=cached_length,
    )


# semantic
def retrieve_similar_chunks(
    db: Session,
    query: str,
    limit: int = MAX_CHUNK_RESPONSE
):
    
    query_vector = generate_embeddings(
        [query]
    )[0]

    distance = EmbeddingModel.vector.cosine_distance(
        query_vector
    ).label("distance")

    result = (
        db.query(
            DocumentModel,
            ChunkModel,
            distance
        )
        .join(
            EmbeddingModel,
            EmbeddingModel.id_chunk == ChunkModel.id
        )
        .join(
            DocumentModel,
            DocumentModel.id == ChunkModel.id_document
        )
        .order_by(
            distance
        )
        .limit(limit)
        .all()
    )

    documents = []

    for document, chunk, distance in result:
        score = max(0.0, 1.0 - float(distance))

        if score < MIN_SEMANTIC_SCORE:
            continue

        documents.append(
            DocumentSchema(
                title=document.title,
                url=document.url,
                content=chunk.content,
                score=score,
                provider=document.provider,
                source_type=document.source_type,
                content_type=document.content_type,
                source_reliability=document.source_reliability,
                search_engine=document.search_engine,
                search_category=document.search_category,
                published_at=document.published_at,
                search_score=document.search_score,
            )
        )

    return documents


# lexical
def retrieve_lexical_chunks(
    db: Session,
    query: str,
    limit: int = MAX_CHUNK_RESPONSE
):
    search_query = func.websearch_to_tsquery("english", query)

    rank = func.ts_rank(
        func.to_tsvector("english", ChunkModel.content),
        search_query
    ).label("score")

    result = (
        db.query(
            DocumentModel,
            ChunkModel,
            rank
        )
        .join(
            DocumentModel,
            DocumentModel.id == ChunkModel.id_document
        )
        .filter(
            func.to_tsvector("english", ChunkModel.content).op("@@")(search_query)
        )
        .filter(
            rank > MIN_LEXICAL_SCORE
        )
        .order_by(
            desc(rank)
        )
        .limit(limit)
        .all()
    )

    documents = [
        DocumentSchema(
            title=document.title,
            url=document.url,
            content=chunk.content,
            score=float(score),
            provider=document.provider,
            source_type=document.source_type,
            content_type=document.content_type,
            source_reliability=document.source_reliability,
            search_engine=document.search_engine,
            search_category=document.search_category,
            published_at=document.published_at,
            search_score=document.search_score,
        )
        for document, chunk, score in result
    ]

    if documents:
        return documents

    # PostgreSQL full-text search can be strict for natural-language questions;
    # fallback to keyword overlap keeps lexical mode useful for sparse matches.
    return retrieve_keyword_chunks(
        db=db,
        query=query,
        limit=limit,
    )


def retrieve_keyword_chunks(
    db: Session,
    query: str,
    limit: int = MAX_CHUNK_RESPONSE
):
    terms = extract_query_terms(query)

    if not terms:
        return []

    rank = sum(
        case(
            (ChunkModel.content.ilike(f"%{term}%"), 1),
            else_=0,
        )
        for term in terms
    ).label("score")

    result = (
        db.query(
            DocumentModel,
            ChunkModel,
            rank
        )
        .join(
            DocumentModel,
            DocumentModel.id == ChunkModel.id_document
        )
        .filter(
            or_(
                *[
                    ChunkModel.content.ilike(f"%{term}%")
                    for term in terms
                ]
            )
        )
        .order_by(
            desc(rank)
        )
        .limit(limit)
        .all()
    )

    max_score = max(
        [score for _, _, score in result],
        default=1,
    )

    return [
        DocumentSchema(
            title=document.title,
            url=document.url,
            content=chunk.content,
            score=float(score) / max_score,
            provider=document.provider,
            source_type=document.source_type,
            content_type=document.content_type,
            source_reliability=document.source_reliability,
            search_engine=document.search_engine,
            search_category=document.search_category,
            published_at=document.published_at,
            search_score=document.search_score,
        )
        for document, chunk, score in result
        if score > 0
    ]


def extract_query_terms(query: str):
    stopwords = {
        "are",
        "can",
        "for",
        "how",
        "the",
        "what",
        "when",
        "where",
        "which",
        "who",
        "why",
        "with",
    }

    return [
        term
        for term in re.findall(r"\b[a-zA-Z0-9]{3,}\b", query.lower())
        if term not in stopwords
    ]


def select_reranker_candidates(
    documents: list[DocumentSchema],
    limit: int,
):
    # First pass favors source diversity; second pass fills remaining slots with
    # the best leftover chunks regardless of URL.
    selected_documents = []
    selected_urls = set()

    for document in documents:
        if document.url in selected_urls:
            continue

        selected_documents.append(document)
        selected_urls.add(document.url)

        if len(selected_documents) >= limit:
            return selected_documents

    selected_document_ids = {
        id(document)
        for document in selected_documents
    }

    for document in documents:
        if id(document) in selected_document_ids:
            continue

        selected_documents.append(document)

        if len(selected_documents) >= limit:
            break

    return selected_documents


def classify_source_type(
    url: str,
    category: str | None = None,
    engine: str | None = None,
):
    domain = urlparse(url).netloc.lower()
    metadata = f"{category or ''} {engine or ''}".lower()

    if any(keyword in metadata for keyword in {"arxiv", "pubmed", "semantic scholar", "science"}):
        return "academic"

    if "news" in metadata:
        return "news"

    if any(
        domain.endswith(academic_domain)
        for academic_domain in {
            "arxiv.org",
            "nature.com",
            "sciencedirect.com",
            "ncbi.nlm.nih.gov",
            "pubmed.ncbi.nlm.nih.gov",
            "springer.com",
            "ieee.org",
            "acm.org",
        }
    ):
        return "academic"

    if any(
        domain.endswith(documentation_domain)
        for documentation_domain in {
            "docs.python.org",
            "developer.mozilla.org",
            "docs.microsoft.com",
            "cloud.google.com",
            "docs.aws.amazon.com",
            "openai.com",
        }
    ):
        return "documentation"

    if any(
        domain.endswith(news_domain)
        for news_domain in {
            "bbc.com",
            "reuters.com",
            "apnews.com",
            "nytimes.com",
            "theguardian.com",
        }
    ):
        return "news"

    if any(
        domain.endswith(forum_domain)
        for forum_domain in {
            "reddit.com",
            "stackoverflow.com",
            "stackexchange.com",
            "quora.com",
        }
    ):
        return "forum"

    return "web"


def detect_content_type(
    url: str,
    title: str = "",
    category: str | None = None,
    engine: str | None = None,
):
    domain = urlparse(url).netloc.lower()
    path = urlparse(url).path.lower()
    metadata = f"{title} {category or ''} {engine or ''}".lower()

    if path.endswith(".pdf"):
        return "pdf"

    source_type = classify_source_type(url, category, engine)

    if source_type == "academic":
        return "paper"

    if source_type == "documentation":
        return "documentation"

    if source_type == "news":
        return "news"

    if source_type == "forum":
        return "forum"

    if "blog" in path or "blog" in metadata:
        return "blog"

    if "press" in path or "press release" in metadata:
        return "press_release"

    if domain.startswith("docs."):
        return "documentation"

    return "article"


def calculate_source_reliability(
    url: str,
    category: str | None = None,
    engine: str | None = None,
):
    source_type = classify_source_type(url, category, engine)

    if source_type == "academic":
        return 90

    if source_type == "documentation":
        return 85

    if source_type == "news":
        return 70

    if source_type == "forum":
        return 45

    return 55
