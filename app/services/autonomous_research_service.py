from sqlalchemy.orm import Session

from app.config.retrieval_config import MAX_CACHED_DOCUMENTS
from app.database.database import SessionLocal
from app.models.embedding_model import EmbeddingModel
from app.services.ingestion.document_ingestion_service import create_document_with_chunks
from app.services.persistance.chunk_service import create_chunks
from app.services.persistance.document_service import (
    get_cached_documents_count,
    get_document_by_url,
)
from app.services.persistance.embedding_service import (
    create_embeddings,
    generate_embeddings,
)
from app.services.persistance.query_document_service import ensure_query_document_relation
from app.services.persistance.query_service import get_or_create_query
from app.services.retrieval.retrieval_service import retrieve_web_documents
from app.services.knowledge_enrichment_service import enrich_chunks
from app.services.utils.tracking_service import PipelineTracker


async def save_follow_up_research(
    parent_query: str,
    follow_up_questions: list[str],
    provider: str,
    retrieval_mode: str,
):
    if not follow_up_questions:
        return

    tracker = PipelineTracker(
        provider=f"{provider}-follow-up",
        retrieval_mode=retrieval_mode,
    )

    try:
        with tracker.measure("follow_up_ingestion"):
            for follow_up_question in follow_up_questions:
                await save_follow_up_question_documents(
                    parent_query=parent_query,
                    follow_up_question=follow_up_question,
                    provider=provider,
                    retrieval_mode=retrieval_mode,
                )
    except Exception as error:
        tracker.log(
            {
                "failed": 1,
                "error_type": type(error).__name__,
            }
        )
    finally:
        tracker.finish()


async def save_follow_up_question_documents(
    parent_query: str,
    follow_up_question: str,
    provider: str,
    retrieval_mode: str,
):
    db: Session = SessionLocal()
    chunk_models = []

    try:
        parent_query_model = get_or_create_query(
            db=db,
            query=parent_query,
            query_type="user",
        )

        follow_up_query_model = get_or_create_query(
            db=db,
            query=follow_up_question,
            query_type="follow_up",
            parent_query_id=parent_query_model.id,
        )

        cached_count = get_cached_documents_count(
            db=db,
            query=follow_up_question,
        )

        if cached_count >= MAX_CACHED_DOCUMENTS:
            db.commit()
            return

        documents = await retrieve_web_documents(
            query=follow_up_question,
            cached_length=cached_count,
            provider=provider,
        )

        for document in documents:
            existing_document = get_document_by_url(
                db=db,
                url=document.url,
            )

            if existing_document:
                ensure_query_document_relation(
                    db=db,
                    id_query=follow_up_query_model.id,
                    id_document=existing_document.id,
                )
                continue

            document_model, new_chunks = create_document_with_chunks(
                db=db,
                document=document,
                provider=provider,
            )

            chunk_models.extend(new_chunks)
            ensure_query_document_relation(
                db=db,
                id_query=follow_up_query_model.id,
                id_document=document_model.id,
            )

        if not chunk_models:
            db.commit()
            return

        create_chunks(
            db=db,
            chunks=chunk_models,
        )

        vectors = generate_embeddings(
            [
                chunk_model.content
                for chunk_model in chunk_models
            ]
        )

        create_embeddings(
            db=db,
            embeddings=[
                EmbeddingModel(
                    id_chunk=chunk_model.id,
                    vector=vectors[index],
                )
                for index, chunk_model in enumerate(chunk_models)
            ],
        )

        db.commit()

        enrich_chunks(
            chunk_ids=[
                chunk_model.id
                for chunk_model in chunk_models
            ],
            provider=provider,
            retrieval_mode=retrieval_mode,
        )
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
