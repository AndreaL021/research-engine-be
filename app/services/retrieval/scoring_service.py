from functools import lru_cache
from datetime import datetime

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.config.config import MIN_RERANKER_SCORE, RERANKER_MODEL
from app.schemas.research_schema import DocumentSchema


SOURCE_TYPE_BOOSTS = {
    "academic": 0.08,
    "documentation": 0.07,
    "news": 0.03,
    "web": 0.0,
    "forum": -0.04,
}

CONTENT_TYPE_BOOSTS = {
    "paper": 0.08,
    "documentation": 0.07,
    "pdf": 0.04,
    "article": 0.02,
    "news": 0.02,
    "blog": -0.02,
    "forum": -0.04,
    "press_release": -0.02,
}

MAX_FRESHNESS_BOOST = 0.04


def apply_metadata_boost(
    documents: list[DocumentSchema],
):
    return [
        document.model_copy(
            update={
                "score": calculate_metadata_aware_score(document)
            }
        )
        for document in documents
    ]


def calculate_metadata_aware_score(document: DocumentSchema):
    # Keep metadata as a light boost: relevance should still dominate, but
    # stronger sources should win ties between similarly relevant chunks.
    reliability_boost = (document.source_reliability - 50) / 1000
    freshness_boost = calculate_freshness_boost(document.published_at)

    boosted_score = (
        document.score
        + reliability_boost
        + freshness_boost
        + SOURCE_TYPE_BOOSTS.get(document.source_type, 0)
        + CONTENT_TYPE_BOOSTS.get(document.content_type, 0)
    )

    return min(
        1.0,
        max(0.0, boosted_score)
    )


def calculate_freshness_boost(published_at: str | None):
    if not published_at:
        return 0

    year = parse_year(published_at)

    if not year:
        return 0

    current_year = datetime.utcnow().year
    age = max(0, current_year - year)

    if age <= 1:
        return MAX_FRESHNESS_BOOST

    if age <= 3:
        return MAX_FRESHNESS_BOOST * 0.6

    if age <= 5:
        return MAX_FRESHNESS_BOOST * 0.3

    return 0


def parse_year(value: str):
    try:
        return int(value[:4])
    except (TypeError, ValueError):
        return None


@lru_cache(maxsize=1)
def get_reranker():
    # Loading is expensive, so keep one model instance alive for the process.
    tokenizer = AutoTokenizer.from_pretrained(RERANKER_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(RERANKER_MODEL)
    model.eval()
    return tokenizer, model


def preload_reranker():
    get_reranker()


def rerank_chunks(
    query: str,
    documents: list[DocumentSchema],
    limit: int,
    batch_size: int = 8,
):

    try:
        tokenizer, model = get_reranker()
        raw_scores: list[float] = []

        pairs = [
            [query, document.content]
            for document in documents
        ]

        with torch.no_grad():
            for start in range(0, len(pairs), batch_size):
                batch = pairs[start:start + batch_size]
                inputs = tokenizer(
                    batch,
                    padding=True,
                    truncation=True,
                    return_tensors="pt",
                    max_length=512,
                )
                logits = model(**inputs, return_dict=True).logits.view(-1).float()
                raw_scores.extend(
                    torch.sigmoid(logits).tolist()
                )
    except Exception:
        return documents[:limit]

    # Cross-encoder scores are useful as an ordering signal, not as calibrated
    # probabilities, so normalize them within the current candidate set.
    scores = normalize_scores(raw_scores)

    reranked_documents = [
        document.model_copy(
            update={
                "score": scores[index]
            }
        )
        for index, document in enumerate(documents)
    ]

    reranked_documents.sort(
        key=lambda document: document.score,
        reverse=True,
    )

    return [
        document
        for document in reranked_documents
        if document.score >= MIN_RERANKER_SCORE
    ][:limit]


def normalize_scores(scores: list[float]):
    if not scores:
        return []

    min_score = min(scores)
    max_score = max(scores)

    if max_score == min_score:
        return [1.0 for _ in scores]

    return [
        (score - min_score) / (max_score - min_score)
        for score in scores
    ]
