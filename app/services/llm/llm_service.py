from functools import lru_cache

from transformers import AutoModelForCausalLM, AutoTokenizer
import torch

from app.config.config import LLM_MODEL


@lru_cache(maxsize=1)
def get_llm():
    tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL)
    model = AutoModelForCausalLM.from_pretrained(LLM_MODEL)
    model.eval()
    return tokenizer, model


def preload_llm():
    get_llm()


def generate_answer(query: str, documents):
    if not documents:
        return "I could not find enough evidence in the retrieved sources to answer the question."

    tokenizer, model = get_llm()

    context = "\n\n".join(
        [
            f"Source {index + 1}: {document.title}\nURL: {document.url}\nContent: {document.content}"
            for index, document in enumerate(documents)
        ]
    )

    prompt = f"""
You are a research assistant. Answer only using the provided sources.
If the sources are insufficient, say that the evidence is insufficient.
Cite sources using [Source 1], [Source 2], etc.

Question:
{query}

Sources:
{context}

Answer:
"""

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
        truncation=True,
        max_length=2048,
    )

    with torch.no_grad():
        output = model.generate(
            **inputs,
            max_new_tokens=300,
            do_sample=False,
        )

    generated_text = tokenizer.decode(
        output[0],
        skip_special_tokens=True,
    )

    if "Answer:" in generated_text:
        return generated_text.split("Answer:", 1)[1].strip()

    return generated_text.strip()
