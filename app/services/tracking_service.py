from contextlib import contextmanager
from hashlib import sha256
from time import perf_counter

from app.config.config import LLM_PROVIDER, TRACKIO_PROJECT


try:
    import trackio
except ImportError:
    trackio = None


class PipelineTracker:
    def __init__(
        self,
        query: str,
        provider: str,
        retrieval_mode: str,
    ):
        self.metrics = {}
        self.enabled = trackio is not None
        self.started_at = perf_counter()

        if self.enabled:
            trackio.init(
                project=TRACKIO_PROJECT,
                name=f"{provider}-{retrieval_mode}",
                group="research-request",
                config={
                    "query_hash": hash_query(query),
                    "query_length": len(query),
                    "provider": provider,
                    "retrieval_mode": retrieval_mode,
                    "llm_provider": LLM_PROVIDER,
                },
            )

    @contextmanager
    def measure(self, name: str):
        started_at = perf_counter()

        try:
            yield
        finally:
            self.metrics[f"{name}_seconds"] = perf_counter() - started_at

    def log(
        self,
        values: dict,
    ):
        self.metrics.update(values)

    def finish(self):
        self.metrics["total_seconds"] = perf_counter() - self.started_at

        if not self.enabled:
            return

        trackio.log(self.metrics)
        trackio.finish()


def hash_query(query: str):
    return sha256(
        query.encode("utf-8")
    ).hexdigest()[:12]
