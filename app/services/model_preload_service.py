from app.services.llm.llm_service import preload_llm
from app.services.persistance.embedding_service import preload_embedding_model
from app.services.retrieval.scoring_service import preload_reranker


def preload_models():
    preload_embedding_model()
    preload_reranker()
    preload_llm()
