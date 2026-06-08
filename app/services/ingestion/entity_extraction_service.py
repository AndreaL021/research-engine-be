import json
import re

import httpx

from app.config.knowledge_config import MAX_ENTITIES_PER_CHUNK
from app.config.llm_config import (
    ENTITY_EXTRACTION_MAX_TOKENS,
    LLM_TEMPERATURE,
    LLM_TIMEOUT_SECONDS,
)
from app.config.model_config import OLLAMA_MODEL, OLLAMA_URL


def extract_entities(content: str):
    response = httpx.post(
        f"{get_ollama_url()}/api/generate",
        json={
            "model": get_ollama_model(),
            "prompt": build_entity_extraction_prompt(content),
            "stream": False,
            "options": {
                "num_predict": ENTITY_EXTRACTION_MAX_TOKENS,
                "temperature": LLM_TEMPERATURE,
            },
        },
        timeout=LLM_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    output = response.json().get("response", "")
    return parse_entities_output(output)


def build_entity_extraction_prompt(content: str):
    return f"""
Extract up to {MAX_ENTITIES_PER_CHUNK} important entities from the text below.
Return only valid JSON.
Do not include explanations.

Entities can be people, organizations, technologies, scientific concepts, places, datasets, methods, products, or named topics.
Prefer specific entities over generic words.

Each entity must have:
- name: concise entity name

Text:
{content}

JSON:
"""


def parse_entities_output(output: str):
    try:
        json_text = extract_json_array(output)
        data = json.loads(json_text)
    except (json.JSONDecodeError, ValueError):
        return parse_entities_from_text(output)

    if not isinstance(data, list):
        return []

    entities = []
    seen_entities = set()

    for item in data[:MAX_ENTITIES_PER_CHUNK]:
        entity_name = parse_entity_name(item)

        if not is_valid_entity(entity_name):
            continue

        normalized_entity = entity_name.lower()

        if normalized_entity in seen_entities:
            continue

        seen_entities.add(normalized_entity)
        entities.append(entity_name)

    return entities


def parse_entities_from_text(output: str):
    entities = []
    seen_entities = set()

    for line in output.splitlines():
        entity_name = clean_entity(line)

        if not is_valid_entity(entity_name):
            continue

        normalized_entity = entity_name.lower()

        if normalized_entity in seen_entities:
            continue

        seen_entities.add(normalized_entity)
        entities.append(entity_name)

        if len(entities) >= MAX_ENTITIES_PER_CHUNK:
            break

    return entities


def parse_entity_name(item):
    if isinstance(item, str):
        return clean_entity(item)

    if isinstance(item, dict):
        return clean_entity(str(item.get("name", "")))

    return ""


def extract_json_array(output: str):
    start = output.find("[")
    end = output.rfind("]")

    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON array found in entity extraction output")

    return output[start:end + 1]


def clean_entity(value: str):
    entity = re.sub(
        r"\s+",
        " ",
        value,
    ).strip()

    return entity.strip("-:;,. ")


def is_valid_entity(entity: str):
    if not entity:
        return False

    if len(entity) < 3 or len(entity) > 80:
        return False

    return not entity.endswith("?")


def get_ollama_url():
    if not OLLAMA_URL:
        raise ValueError("OLLAMA_URL is required")

    return OLLAMA_URL.rstrip("/")


def get_ollama_model():
    if not OLLAMA_MODEL:
        raise ValueError("OLLAMA_MODEL is required")

    return OLLAMA_MODEL
