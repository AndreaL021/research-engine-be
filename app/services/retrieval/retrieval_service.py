from sqlalchemy.orm import Session

from app.config.retrieval_config import MAX_CHUNK_RESPONSE, RERANKER_CANDIDATES
from app.services.retrieval.local.candidate_service import (
    assign_source_numbers,
    select_reranker_candidates,
)
from app.services.retrieval.local.chunk_retrieval_service import (
    retrieve_lexical_chunks,
    retrieve_similar_chunks,
)
from app.services.retrieval.providers.ddgs_provider import (
    retrieve_web_documents as retrieve_ddgs_documents,
)
from app.services.retrieval.providers.exa_provider import (
    retrieve_web_documents as retrieve_exa_documents,
)
from app.services.retrieval.providers.searxng_provider import (
    retrieve_web_documents as retrieve_searxng_documents,
)
from app.services.retrieval.local.scoring_service import (
    apply_metadata_boost,
    rerank_chunks,
)
from app.services.utils.tracking_service import PipelineTracker


def retrieve_chunks(
    db: Session,
    query: str,
    retrieval_mode: str,
    tracker: PipelineTracker | None = None,
):
    documents = retrieve_initial_candidates(
        db=db,
        query=query,
        retrieval_mode=retrieval_mode,
    )

    boosted_documents = apply_metadata_boost(documents)

    sorted_documents = sorted(
        boosted_documents,
        key=lambda document: document.score,
        reverse=True,
    )

    documents = select_reranker_candidates(
        sorted_documents,
        limit=RERANKER_CANDIDATES,
    )

    if tracker:
        with tracker.measure("reranker"):
            reranked_documents = rerank_chunks(
                query=query,
                documents=documents,
                limit=MAX_CHUNK_RESPONSE,
            )
    else:
        reranked_documents = rerank_chunks(
            query=query,
            documents=documents,
            limit=MAX_CHUNK_RESPONSE,
        )

    return assign_source_numbers(reranked_documents)


async def retrieve_web_documents(
    query: str,
    cached_length: int,
    provider: str,
):
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


def retrieve_initial_candidates(
    db: Session,
    query: str,
    retrieval_mode: str,
):
    if retrieval_mode == "lexical":
        return retrieve_lexical_chunks(
            db=db,
            query=query,
            limit=MAX_CHUNK_RESPONSE,
        )

    return retrieve_similar_chunks(
        db=db,
        query=query,
        limit=MAX_CHUNK_RESPONSE,
    )

