import re

from sqlalchemy.orm import Session

from app.models.claim_model import ClaimModel


MAX_CLAIMS_PER_CHUNK = 3
MIN_CLAIM_WORDS = 8
MAX_CLAIM_WORDS = 45

CLAIM_SIGNAL_WORDS = {
    "affect",
    "allow",
    "because",
    "can",
    "cause",
    "depend",
    "enable",
    "improve",
    "increase",
    "indicate",
    "lead",
    "may",
    "reduce",
    "require",
    "show",
    "suggest",
}


def create_claims(
    db: Session,
    chunks,
):
    claim_models = []

    for chunk in chunks:
        claims = extract_claims(
            chunk.content
        )

        claim_models.extend(
            [
                ClaimModel(
                    id_document=chunk.id_document,
                    id_chunk=chunk.id,
                    claim_text=claim_text,
                    claim_type=classify_claim_type(claim_text),
                    confidence=calculate_claim_confidence(claim_text),
                )
                for claim_text in claims
            ]
        )

    if not claim_models:
        return []

    db.add_all(claim_models)
    db.flush()

    return claim_models


def extract_claims(content: str):
    sentences = split_sentences(content)
    claims = []
    seen_claims = set()

    for sentence in sentences:
        claim = clean_claim(sentence)

        if not is_valid_claim(claim):
            continue

        normalized_claim = claim.lower()

        if normalized_claim in seen_claims:
            continue

        seen_claims.add(normalized_claim)
        claims.append(claim)

        if len(claims) >= MAX_CLAIMS_PER_CHUNK:
            break

    return claims


def split_sentences(content: str):
    return re.split(
        r"(?<=[.!?])\s+",
        content,
    )


def clean_claim(sentence: str):
    claim = re.sub(
        r"\s+",
        " ",
        sentence,
    ).strip()

    return claim.strip("-:; ")


def is_valid_claim(claim: str):
    words = claim.split()

    if len(words) < MIN_CLAIM_WORDS or len(words) > MAX_CLAIM_WORDS:
        return False

    if claim.endswith("?"):
        return False

    lowered_claim = claim.lower()

    return any(
        signal_word in lowered_claim
        for signal_word in CLAIM_SIGNAL_WORDS
    )


def classify_claim_type(claim: str):
    lowered_claim = claim.lower()

    if any(word in lowered_claim for word in {"however", "but", "although", "whereas"}):
        return "contrast"

    if any(word in lowered_claim for word in {"unknown", "unclear", "insufficient", "limited"}):
        return "uncertainty"

    return "evidence"


def calculate_claim_confidence(claim: str):
    confidence = 55
    lowered_claim = claim.lower()

    if any(word in lowered_claim for word in {"show", "indicate", "suggest"}):
        confidence += 10

    if any(word in lowered_claim for word in {"may", "could", "might"}):
        confidence -= 10

    if classify_claim_type(claim) == "uncertainty":
        confidence -= 15

    return max(
        20,
        min(90, confidence),
    )
