from functools import lru_cache

import torch
from transformers import AutoModelForSequenceClassification, AutoTokenizer

from app.config.config import (RERANKER_MODEL, MIN_RERANKER_SCORE)
from app.schemas.research_schema import DocumentSchema


@lru_cache(maxsize=1)
def get_reranker():
    tokenizer = AutoTokenizer.from_pretrained(RERANKER_MODEL)
    model = AutoModelForSequenceClassification.from_pretrained(RERANKER_MODEL)
    model.eval()
    return tokenizer, model


def rerank_chunks(
    query: str,
    documents: list[DocumentSchema],
    limit: int,
    batch_size: int = 8,
):

    try:
        tokenizer, model = get_reranker()
        scores: list[float] = []

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
                scores.extend(
                    torch.sigmoid(logits).tolist()
                )
    except Exception:
        return documents[:limit]

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
