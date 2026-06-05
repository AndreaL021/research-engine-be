from functools import lru_cache
import re

import httpx
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

from app.config.llm_config import (
    LLM_INPUT_MAX_LENGTH,
    LLM_MAX_NEW_TOKEN,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
    MIN_ANSWER_DOCUMENTS,
    MIN_AVERAGE_ANSWER_SCORE,
    MIN_AVERAGE_SOURCE_RELIABILITY,
    OLLAMA_KEEP_ALIVE,
    OLLAMA_PRELOAD_TOKENS,
)
from app.config.model_config import (
    LLM_MODEL,
    LLM_PROVIDER,
    OLLAMA_MODEL,
    OLLAMA_URL,
)
from app.services.llm.context_builder_service import build_answer_context


@lru_cache(maxsize=1)
def get_huggingface_llm():
    tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL)
    model = AutoModelForCausalLM.from_pretrained(LLM_MODEL)
    model.eval()
    return tokenizer, model


def preload_llm():
    if is_ollama_provider():
        preload_ollama_llm()
        return

    get_huggingface_llm()


def generate_answer(query: str, documents):
    evidence_status = evaluate_evidence_status(documents)

    if evidence_status == "insufficient":
        return build_insufficient_evidence_answer(documents)

    context = build_answer_context(documents)
    prompt = build_answer_prompt(
        query=query,
        context=context,
        evidence_status=evidence_status,
    )

    if is_ollama_provider():
        answer = generate_ollama_answer(prompt)
        return normalize_citations(
            answer=answer,
            source_count=min(len(documents), 3),
        )

    answer = generate_huggingface_answer(prompt)
    return normalize_citations(
        answer=answer,
        source_count=min(len(documents), 3),
    )


def build_answer_prompt(
    query: str,
    context: str,
    evidence_status: str,
):
    evidence_instruction = build_evidence_instruction(evidence_status)

    return f"""
You answer questions using only the stored evidence below.
Do not use outside knowledge.
{evidence_instruction}

Do not summarize sources one by one.
Combine evidence across sources.
Return exactly 3 bullets.
Each bullet must be one sentence.
Each bullet must end with citations like [Source 1].
If you cannot cite a bullet, do not include it.

Question:
{query}

Sources:
{context}

Answer:
"""


def evaluate_evidence_status(documents):
    if not documents:
        return "insufficient"

    if len(documents) < MIN_ANSWER_DOCUMENTS:
        return "limited"

    average_score = sum(document.score for document in documents) / len(documents)
    average_reliability = sum(document.source_reliability for document in documents) / len(documents)

    if average_score < MIN_AVERAGE_ANSWER_SCORE:
        return "insufficient"

    if average_reliability < MIN_AVERAGE_SOURCE_RELIABILITY:
        return "limited"

    return "sufficient"


def build_evidence_instruction(evidence_status: str):
    if evidence_status == "limited":
        return "The available evidence is limited. Start the answer with: \"The available evidence is limited.\""

    return "The available evidence is sufficient for a concise grounded answer."


def build_insufficient_evidence_answer(documents):
    if not documents:
        return "The retrieved evidence is insufficient to answer confidently. No relevant stored sources were found."

    return "The retrieved evidence is insufficient to answer confidently. The available sources are too weak or not relevant enough."


def generate_huggingface_answer(prompt: str):
    tokenizer, model = get_huggingface_llm()

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=LLM_INPUT_MAX_LENGTH,
    )

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=LLM_MAX_NEW_TOKEN,
            do_sample=False,
        )

    generated_text = tokenizer.decode(
        output[0],
        skip_special_tokens=True,
    )

    if "Answer:" in generated_text:
        return generated_text.split("Answer:", 1)[1].strip()

    return generated_text.strip()


def generate_ollama_answer(prompt: str):
    response = httpx.post(
        f"{get_ollama_url()}/api/generate",
        json={
            "model": get_ollama_model(),
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": LLM_MAX_NEW_TOKEN,
                "temperature": LLM_TEMPERATURE,
            },
        },
        timeout=LLM_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    return response.json().get("response", "").strip()


def normalize_citations(
    answer: str,
    source_count: int,
):
    bullets = extract_answer_bullets(answer)

    if not bullets:
        return answer.strip()

    normalized_bullets = []

    for index, bullet in enumerate(bullets[:3]):
        if has_source_citation(bullet):
            normalized_bullets.append(bullet)
            continue

        source_number = min(index + 1, max(1, source_count))
        normalized_bullets.append(
            f"{bullet} [Source {source_number}]"
        )

    return "\n".join(
        f"- {bullet}"
        for bullet in normalized_bullets
    )


def extract_answer_bullets(answer: str):
    lines = [
        clean_answer_line(line)
        for line in answer.splitlines()
    ]

    bullets = [
        line
        for line in lines
        if line
    ]

    if len(bullets) == 1:
        bullets = re.split(
            r"(?<=[.!?])\s+",
            bullets[0],
        )

    return [
        bullet.strip()
        for bullet in bullets
        if bullet.strip()
    ]


def clean_answer_line(line: str):
    return re.sub(
        r"^\s*[-*\d.)]+\s*",
        "",
        line,
    ).strip()


def has_source_citation(text: str):
    return bool(
        re.search(
            r"\[Source\s+\d+\]",
            text,
        )
    )


def preload_ollama_llm():
    # Ask Ollama to load the model at application startup, so the first answer
    # request does not pay the full model load cost.
    response = httpx.post(
        f"{get_ollama_url()}/api/generate",
        json={
            "model": get_ollama_model(),
            "prompt": "",
            "stream": False,
            "keep_alive": OLLAMA_KEEP_ALIVE,
            "options": {
                "num_predict": OLLAMA_PRELOAD_TOKENS,
                "temperature": LLM_TEMPERATURE,
            },
        },
        timeout=LLM_TIMEOUT_SECONDS,
    )
    response.raise_for_status()


def is_ollama_provider():
    return LLM_PROVIDER.lower() == "ollama"


def get_ollama_url():
    if not OLLAMA_URL:
        raise ValueError("OLLAMA_URL is required when LLM_PROVIDER=ollama")

    return OLLAMA_URL.rstrip("/")


def get_ollama_model():
    model = OLLAMA_MODEL or LLM_MODEL

    if not model:
        raise ValueError("OLLAMA_MODEL or LLM_MODEL is required when LLM_PROVIDER=ollama")

    return model
