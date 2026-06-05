import os

from dotenv import load_dotenv

load_dotenv()


EXA_API_KEY = os.getenv("EXA_API_KEY")
SEARXNG_URL = os.getenv("SEARXNG_URL")

MAX_RESULTS = 10
MAX_CACHED_DOCUMENTS = 5

MIN_CONTENT_WORDS = 20
MAX_TRAFILATURA_DOWNLOADS = 5
SEARXNG_CATEGORY = "general"
DDGS_BACKEND = "duckduckgo"
SEARXNG_TIMEOUT_SECONDS = 10.0

MAX_CHUNK_RESPONSE = 30
MIN_SEMANTIC_SCORE = 0.2
MIN_LEXICAL_SCORE = 0.0
MIN_RERANKER_SCORE = 0.2
RERANKER_CANDIDATES = 10
RERANKER_BATCH_SIZE = 8
RERANKER_MAX_LENGTH = 512

SOURCE_TYPE_BOOSTS = {
    "academic": 0.08,
    "documentation": 0.07,
    "news": 0.03,
    "web": 0.0,
    "forum": -0.04,
}

CONTENT_TYPE_BOOSTS = {
    "paper": 0.08,
    "documentation": 0.07,
    "pdf": 0.04,
    "article": 0.02,
    "news": 0.02,
    "blog": -0.02,
    "forum": -0.04,
    "press_release": -0.02,
}

MAX_FRESHNESS_BOOST = 0.04

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
