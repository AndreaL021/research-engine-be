from contextlib import contextmanager
from time import perf_counter

import trackio

from app.config.tracking_config import TRACKING_ENABLED, TRACKIO_PROJECT


class PipelineTracker:
    def __init__(
        self,
        provider: str,
        retrieval_mode: str,
    ):
        self.metrics = {}
        self.enabled = TRACKING_ENABLED
        self.started_at = perf_counter()

        if self.enabled:
            trackio.init(
                project=TRACKIO_PROJECT,
                name=f"{provider}-{retrieval_mode}",
                group="research-request",
                config={
                    "provider": provider,
                    "retrieval_mode": retrieval_mode,
                },
            )

    @contextmanager
    def measure(self, name: str):
        started_at = perf_counter()

        try:
            yield
        finally:
            metric_name = f"{name}_seconds"
            elapsed_seconds = perf_counter() - started_at
            self.metrics[metric_name] = self.metrics.get(metric_name, 0) + elapsed_seconds

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
