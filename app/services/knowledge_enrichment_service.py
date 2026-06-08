from app.services.persistance.claim_service import create_claims_for_chunk_ids
from app.services.persistance.entity_service import create_entities_for_chunk_ids


def enrich_chunks(
    chunk_ids: list[int],
    provider: str,
    retrieval_mode: str,
):
    if not chunk_ids:
        return

    create_claims_for_chunk_ids(
        chunk_ids=chunk_ids,
        provider=provider,
        retrieval_mode=retrieval_mode,
    )

    create_entities_for_chunk_ids(
        chunk_ids=chunk_ids,
        provider=provider,
        retrieval_mode=retrieval_mode,
    )
