import os

from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

EXA_API_KEY = os.getenv("EXA_API_KEY")

RETRIEVAL_PROVIDER = "ddgs"

MAX_RESULTS = 5

MIN_CONTENT_WORDS = 20

MAX_CACHED_DOCUMENTS = 10

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

CHUNK_SIZE = 200

CHUNK_OVERLAP = 50