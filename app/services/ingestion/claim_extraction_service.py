import json
import re

import httpx

from app.config.knowledge_config import (
    MAX_CLAIMS_PER_CHUNK,
    MAX_CLAIM_WORDS,
    MIN_CLAIM_WORDS,
)
from app.config.llm_config import (
    CLAIM_EXTRACTION_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
)
from app.config.model_config import OLLAMA_MODEL, OLLAMA_URL


def extract_claims(content: str):
    return extract_claims_with_ollama(content)


def extract_claims_with_ollama(content: str):
    response = httpx.post(
        f"{get_ollama_url()}/api/generate",
        json={
            "model": get_ollama_model(),
            "prompt": build_claim_extraction_prompt(content),
            "stream": False,
            "options": {
                "num_predict": CLAIM_EXTRACTION_MAX_TOKENS,
                "temperature": LLM_TEMPERATURE,
            },
        },
        timeout=LLM_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    output = response.json().get("response", "")
    return parse_claims_json(output)


def build_claim_extraction_prompt(content: str):
    return f"""
Extract up to {MAX_CLAIMS_PER_CHUNK} factual claims from the text below.
Return only valid JSON.
Do not include explanations.

Each claim must have:
- claim_text: one concise factual claim
- claim_type: one of evidence, contrast, uncertainty
- confidence: integer from 0 to 100

Text:
{content}

JSON:
"""


def parse_claims_json(output: str):
    json_text = extract_json_array(output)
    data = json.loads(json_text)

    if not isinstance(data, list):
        return []

    claims = []
    seen_claims = set()

    for item in data[:MAX_CLAIMS_PER_CHUNK]:
        if not isinstance(item, dict):
            continue

        claim_text = clean_claim(str(item.get("claim_text", "")))

        if not is_valid_claim_text(claim_text):
            continue

        normalized_claim = claim_text.lower()

        if normalized_claim in seen_claims:
            continue

        seen_claims.add(normalized_claim)
        claims.append(
            {
                "claim_text": claim_text,
                "claim_type": normalize_claim_type(item.get("claim_type")),
                "confidence": normalize_confidence(item.get("confidence")),
            }
        )

    return claims


def extract_json_array(output: str):
    start = output.find("[")
    end = output.rfind("]")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON array found in claim extraction output")

    return output[start:end + 1]


def clean_claim(sentence: str):
    claim = re.sub(
        r"\s+",
        " ",
        sentence,
    ).strip()

    return claim.strip("-:; ")


def is_valid_claim_text(claim: str):
    words = claim.split()

    if len(words) < MIN_CLAIM_WORDS or len(words) > MAX_CLAIM_WORDS:
        return False

    return not claim.endswith("?")


def normalize_claim_type(value):
    claim_type = str(value or "").lower()

    if claim_type in {"evidence", "contrast", "uncertainty"}:
        return claim_type

    return "evidence"


def normalize_confidence(value):
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 50

    if confidence <= 1:
        confidence *= 100

    return max(
        0,
        min(100, int(confidence)),
    )


def get_ollama_url():
    if not OLLAMA_URL:
        raise ValueError("OLLAMA_URL is required")

    return OLLAMA_URL.rstrip("/")


def get_ollama_model():
    if not OLLAMA_MODEL:
        raise ValueError("OLLAMA_MODEL is required")

    return OLLAMA_MODEL
