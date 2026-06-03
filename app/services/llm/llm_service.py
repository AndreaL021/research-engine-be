from functools import lru_cache

import httpx
from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

from app.config.config import (
    LLM_MODEL,
    LLM_MAX_NEW_TOKEN,
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
    if not documents:
        return "I could not find enough evidence in the retrieved sources to answer the question."

    context = build_answer_context(documents)
    prompt = build_answer_prompt(
        query=query,
        context=context,
    )

    if is_ollama_provider():
        return generate_ollama_answer(prompt)

    return generate_huggingface_answer(prompt)


def build_answer_prompt(
    query: str,
    context: str,
):
    return f"""
You are a research engine that extracts useful evidence from a pre-built knowledge base.
Use only the provided sources. Do not use outside knowledge.

Write a compact answer using exactly this format:
- Finding: one relevant finding in one sentence. Evidence: cite sources with [Source 1].
- Finding: one relevant finding in one sentence. Evidence: cite sources with [Source 2].

Rules:
- Write 3 to 5 bullets maximum.
- Each bullet must be short and evidence-focused.
- Every bullet must include at least one source citation.
- Do not write paragraphs, introductions, conclusions, or numbered lists.
- If sources disagree, add one short bullet about the disagreement.
- If evidence is missing or weak, add one short bullet about what is unknown.
- Stop after the final bullet.

Question:
{query}

Sources:
{context}

Answer:
"""


def generate_huggingface_answer(prompt: str):
    tokenizer, model = get_huggingface_llm()

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=2048,
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
                "temperature": 0,
            },
        },
        timeout=180,
    )
    response.raise_for_status()

    return response.json().get("response", "").strip()


def preload_ollama_llm():
    # Ask Ollama to load the model at application startup, so the first answer
    # request does not pay the full model load cost.
    response = httpx.post(
        f"{get_ollama_url()}/api/generate",
        json={
            "model": get_ollama_model(),
            "prompt": "",
            "stream": False,
            "keep_alive": "30m",
            "options": {
                "num_predict": 1,
                "temperature": 0,
            },
        },
        timeout=180,
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
