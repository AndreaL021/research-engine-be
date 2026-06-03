import os
from dotenv import load_dotenv
load_dotenv()

# config
DATABASE_URL = os.getenv("DATABASE_URL")
EXA_API_KEY = os.getenv("EXA_API_KEY")
SEARXNG_URL = os.getenv("SEARXNG_URL")
CHUNK_SIZE = 200
CHUNK_OVERLAP = 50
MAX_CHUNK_RESPONSE = 30
MIN_SEMANTIC_SCORE = 0.2
MIN_LEXICAL_SCORE = 0.0
MIN_RERANKER_SCORE = 0.2
RERANKER_CANDIDATES = 10
LLM_CONTEXT_CHUNKS = 5
LLM_MAX_NEW_TOKEN = 260
# huggingface models
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL")
RERANKER_MODEL = os.getenv("RERANKER_MODEL")
LLM_MODEL = os.getenv("LLM_MODEL")
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "huggingface")
OLLAMA_URL = os.getenv("OLLAMA_URL")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL")
# tracking
TRACKIO_PROJECT = "research-engine"
# search
RETRIEVAL_PROVIDER = "searxng"
MAX_RESULTS = 10
# check
MIN_CONTENT_WORDS = 20
MAX_CACHED_DOCUMENTS = 5
BLOCKED_DOMAINS = {
    "facebook.com",
    "instagram.com",
    "pinterest.com",
    "tiktok.com",
    "linkedin.com",
    "x.com",
    "twitter.com",
    "youtube.com",
}
TRUSTED_DOMAINS = {
    "wikipedia.org",
    "arxiv.org",
    "nature.com",
    "sciencedirect.com",
    "ncbi.nlm.nih.gov",
    "github.com",
    "openai.com",
}
