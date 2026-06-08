import json

import httpx

from app.config.knowledge_config import CLAIM_RECONCILIATION_MAX_TOKENS
from app.config.llm_config import LLM_TEMPERATURE, LLM_TIMEOUT_SECONDS
from app.config.model_config import OLLAMA_MODEL, OLLAMA_URL


def reconcile_claims(
    claim_a: str,
    claim_b: str,
):
    response = httpx.post(
        f"{get_ollama_url()}/api/generate",
        json={
            "model": get_ollama_model(),
            "prompt": build_reconciliation_prompt(
                claim_a=claim_a,
                claim_b=claim_b,
            ),
            "stream": False,
            "options": {
                "num_predict": CLAIM_RECONCILIATION_MAX_TOKENS,
                "temperature": LLM_TEMPERATURE,
            },
        },
        timeout=LLM_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    output = response.json().get("response", "")
    return parse_reconciliation_json(output)


def build_reconciliation_prompt(
    claim_a: str,
    claim_b: str,
):
    return f"""
Compare the two claims below.
Return only valid JSON.
Do not include explanations outside JSON.

relation_type must be one of:
- agreement
- contradiction
- partial
- unrelated

Claim A:
{claim_a}

Claim B:
{claim_b}

JSON object:
{{
  "relation_type": "...",
  "confidence": 0,
  "explanation": "short reason"
}}
"""


def parse_reconciliation_json(output: str):
    data = json.loads(extract_json_object(output))

    relation_type = normalize_relation_type(
        data.get("relation_type")
    )

    return {
        "relation_type": relation_type,
        "confidence": normalize_confidence(data.get("confidence")),
        "explanation": str(data.get("explanation", "")).strip()[:500],
    }


def extract_json_object(output: str):
    start = output.find("{")
    end = output.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in claim reconciliation output")

    return output[start:end + 1]


def normalize_relation_type(value):
    relation_type = str(value or "").lower().strip()

    if relation_type in {"agreement", "contradiction", "partial", "unrelated"}:
        return relation_type

    return "unrelated"


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
