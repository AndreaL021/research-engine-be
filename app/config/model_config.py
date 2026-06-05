import os

from dotenv import load_dotenv

load_dotenv()


EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
RERANKER_MODEL = os.getenv("RERANKER_MODEL")
LLM_MODEL = os.getenv("LLM_MODEL")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "huggingface")
OLLAMA_URL = os.getenv("OLLAMA_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
