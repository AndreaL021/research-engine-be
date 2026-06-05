from sqlalchemy.orm import Session

from app.database.database import SessionLocal
from app.models.chunk_model import ChunkModel
from app.models.claim_model import ClaimModel
from app.services.ingestion.claim_extraction_service import extract_claims
from app.services.utils.tracking_service import PipelineTracker


def create_claims(
    db: Session,
    chunks,
):
    claim_models = []

    for chunk in chunks:
        try:
            claims = extract_claims(chunk.content)
        except Exception:
            continue

        claim_models.extend(
            [
                ClaimModel(
                    id_document=chunk.id_document,
                    id_chunk=chunk.id,
                    claim_text=claim["claim_text"],
                    claim_type=claim["claim_type"],
                    confidence=claim["confidence"],
                )
                for claim in claims
            ]
        )

    if not claim_models:
        return []

    db.add_all(claim_models)
    db.flush()

    return claim_models


def create_claims_for_chunk_ids(
    chunk_ids: list[int],
    provider: str,
    retrieval_mode: str,
):
    db: Session = SessionLocal()
    tracker = PipelineTracker(
        provider=f"{provider}-claims",
        retrieval_mode=retrieval_mode,
    )

    try:
        chunks = (
            db.query(ChunkModel)
            .filter(ChunkModel.id.in_(chunk_ids))
            .all()
        )

        with tracker.measure("claim_extraction"):
            create_claims(
                db=db,
                chunks=chunks,
            )

        db.commit()
    except Exception as error:
        db.rollback()
        tracker.log(
            {
                "failed": 1,
                "error_type": type(error).__name__,
            }
        )
    finally:
        tracker.finish()
        db.close()
