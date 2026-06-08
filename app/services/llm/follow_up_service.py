import json
import re

import httpx

from app.config.llm_config import (
    FOLLOW_UP_MAX_TOKENS,
    FOLLOW_UP_QUESTIONS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
)
from app.config.model_config import OLLAMA_MODEL, OLLAMA_URL


def generate_follow_up_questions(
    query: str,
    documents,
):
    if not documents:
        return []

    try:
        response = httpx.post(
            f"{get_ollama_url()}/api/generate",
            json={
                "model": get_ollama_model(),
                "prompt": build_follow_up_prompt(
                    query=query,
                    documents=documents,
                ),
                "stream": False,
                "options": {
                    "num_predict": FOLLOW_UP_MAX_TOKENS,
                    "temperature": LLM_TEMPERATURE,
                },
            },
            timeout=LLM_TIMEOUT_SECONDS,
        )
        response.raise_for_status()

        output = response.json().get("response", "")
        return parse_follow_up_questions(output)
    except Exception:
        return []


def build_follow_up_prompt(
    query: str,
    documents,
):
    evidence = build_follow_up_evidence(documents)

    return f"""
You are planning the next research steps for a research engine.
Use only the evidence below.
Generate exactly {FOLLOW_UP_QUESTIONS} follow-up research questions that would help fill gaps, verify claims, or explore contradictions.
Return only valid JSON as an array of strings.
Do not include explanations.

Original question:
{query}

Evidence:
{evidence}

JSON:
"""


def build_follow_up_evidence(documents):
    evidence_items = []

    for index, document in enumerate(documents[:5], start=1):
        evidence_items.append(
            f"Source {index}: {document.title}\n{document.content[:500]}"
        )

    return "\n\n".join(evidence_items)


def parse_follow_up_questions(output: str):
    json_text = extract_json_array(output)
    data = json.loads(json_text)

    if not isinstance(data, list):
        return []

    questions = []
    seen_questions = set()

    for item in data[:FOLLOW_UP_QUESTIONS]:
        question = clean_question(str(item))

        if not is_valid_question(question):
            continue

        normalized_question = question.lower()

        if normalized_question in seen_questions:
            continue

        seen_questions.add(normalized_question)
        questions.append(question)

    return questions


def extract_json_array(output: str):
    start = output.find("[")
    end = output.rfind("]")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON array found in follow-up output")

    return output[start:end + 1]


def clean_question(value: str):
    question = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return question.strip("-:;,. ")


def is_valid_question(question: str):
    if len(question.split()) < 4:
        return False

    if len(question) > 180:
        return False

    return question.endswith("?")


def get_ollama_url():
    if not OLLAMA_URL:
        raise ValueError("OLLAMA_URL is required")

    return OLLAMA_URL.rstrip("/")


def get_ollama_model():
    if not OLLAMA_MODEL:
        raise ValueError("OLLAMA_MODEL is required")

    return OLLAMA_MODEL
