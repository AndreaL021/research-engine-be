from sqlalchemy.orm import Session

from app.config.knowledge_config import (
    MAX_RECONCILIATION_CLAIMS,
    MAX_RECONCILIATION_COMPARISONS,
)
from app.database.database import SessionLocal
from app.models.claim_model import ClaimModel
from app.models.claim_relation_model import ClaimRelationModel
from app.services.ingestion.claim_reconciliation_service import reconcile_claims
from app.services.utils.tracking_service import PipelineTracker


def reconcile_claims_for_claim_ids(
    claim_ids: list[int],
    provider: str,
    retrieval_mode: str,
):
    if not claim_ids:
        return

    db: Session = SessionLocal()
    tracker = PipelineTracker(
        provider=f"{provider}-reconciliation",
        retrieval_mode=retrieval_mode,
    )

    try:
        with tracker.measure("claim_reconciliation"):
            new_claims = get_claims_by_ids(
                db=db,
                claim_ids=claim_ids,
            )

            existing_claims = get_existing_comparison_claims(
                db=db,
                excluded_claim_ids=claim_ids,
            )

            create_claim_relations(
                db=db,
                new_claims=new_claims,
                existing_claims=existing_claims,
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


def get_claims_by_ids(
    db: Session,
    claim_ids: list[int],
):
    return (
        db.query(ClaimModel)
        .filter(ClaimModel.id.in_(claim_ids))
        .limit(MAX_RECONCILIATION_CLAIMS)
        .all()
    )


def get_existing_comparison_claims(
    db: Session,
    excluded_claim_ids: list[int],
):
    return (
        db.query(ClaimModel)
        .filter(~ClaimModel.id.in_(excluded_claim_ids))
        .order_by(ClaimModel.created_at.desc())
        .limit(MAX_RECONCILIATION_CLAIMS)
        .all()
    )


def create_claim_relations(
    db: Session,
    new_claims,
    existing_claims,
):
    comparisons = 0

    for claim_a in new_claims:
        for claim_b in existing_claims:
            if comparisons >= MAX_RECONCILIATION_COMPARISONS:
                return

            if claim_a.id_document == claim_b.id_document:
                continue

            if not should_compare_claims(claim_a.claim_text, claim_b.claim_text):
                continue

            relation = compare_and_build_relation(
                claim_a=claim_a,
                claim_b=claim_b,
            )

            comparisons += 1

            if not relation:
                continue

            save_claim_relation(
                db=db,
                id_claim_a=claim_a.id,
                id_claim_b=claim_b.id,
                relation=relation,
            )


def should_compare_claims(
    claim_a: str,
    claim_b: str,
):
    words_a = get_comparison_words(claim_a)
    words_b = get_comparison_words(claim_b)

    return len(words_a.intersection(words_b)) >= 2


def get_comparison_words(claim: str):
    return {
        word.strip(".,;:()[]").lower()
        for word in claim.split()
        if len(word.strip(".,;:()[]")) >= 5
    }


def compare_and_build_relation(
    claim_a,
    claim_b,
):
    try:
        relation = reconcile_claims(
            claim_a=claim_a.claim_text,
            claim_b=claim_b.claim_text,
        )
    except Exception:
        return None

    if relation["relation_type"] == "unrelated":
        return None

    return relation


def save_claim_relation(
    db: Session,
    id_claim_a: int,
    id_claim_b: int,
    relation: dict,
):
    first_claim_id, second_claim_id = sorted(
        [id_claim_a, id_claim_b]
    )

    existing_relation = (
        db.query(ClaimRelationModel)
        .filter(
            ClaimRelationModel.id_claim_a == first_claim_id,
            ClaimRelationModel.id_claim_b == second_claim_id,
        )
        .first()
    )

    if existing_relation:
        return existing_relation

    claim_relation = ClaimRelationModel(
        id_claim_a=first_claim_id,
        id_claim_b=second_claim_id,
        relation_type=relation["relation_type"],
        confidence=relation["confidence"],
        explanation=relation["explanation"],
    )

    db.add(claim_relation)
    db.flush()

    return claim_relation


def get_evidence_relations_for_chunks(
    db: Session,
    chunk_ids: list[int],
    limit: int = 10,
):
    if not chunk_ids:
        return []

    claim_ids = [
        claim_id
        for claim_id, in (
            db.query(ClaimModel.id)
            .filter(ClaimModel.id_chunk.in_(chunk_ids))
            .all()
        )
    ]

    if not claim_ids:
        return []

    relations = (
        db.query(ClaimRelationModel)
        .filter(
            (ClaimRelationModel.id_claim_a.in_(claim_ids))
            | (ClaimRelationModel.id_claim_b.in_(claim_ids))
        )
        .order_by(ClaimRelationModel.created_at.desc())
        .limit(limit)
        .all()
    )

    evidence_relations = []

    for relation in relations:
        claim_a = db.get(ClaimModel, relation.id_claim_a)
        claim_b = db.get(ClaimModel, relation.id_claim_b)

        if not claim_a or not claim_b:
            continue

        evidence_relations.append(
            {
                "relation_type": relation.relation_type,
                "confidence": relation.confidence,
                "explanation": relation.explanation,
                "claim_a": claim_a.claim_text,
                "claim_b": claim_b.claim_text,
            }
        )

    return evidence_relations
