"""Central logging configuration for Flow Builder Engine."""
from __future__ import annotations

import json
import os
import sys
import time
from contextvars import ContextVar
from typing import Any, Dict

from loguru import logger
from prometheus_client import Counter, Histogram, start_http_server

# Context variable for trace id so lower layers can attach it
trace_id_var: ContextVar[str | None] = ContextVar("trace_id", default=None)


class JsonSink:
    """Loguru sink that outputs each record as a JSON line."""

    def __call__(self, message):  # type: ignore[override]
        record = message.record
        log_obj: Dict[str, Any] = {
            "timestamp": record["time"].isoformat(),
            "level": record["level"].name,
            "message": record["message"],
            **record["extra"],
        }
        # Include traceId if present in context
        trace_id = trace_id_var.get()
        if trace_id:
            log_obj["traceId"] = trace_id
        sys.stdout.write(json.dumps(log_obj) + "\n")


def configure_logging():
    """Apply JSON logging configuration. Safe to call multiple times."""

    if any(isinstance(h, JsonSink) for _, h in logger._core.handlers.items()):  # type: ignore[attr-defined]
        return  # Already configured
    logger.remove()
    logger.add(JsonSink(), level=os.getenv("LOG_LEVEL", "INFO"))

    # Start Prometheus exporter on port 8001 (adjustable via env)
    if os.getenv("ENABLE_METRICS", "true").lower() == "true":
        port = int(os.getenv("METRICS_PORT", "8001"))
        start_http_server(port)


# Prometheus metrics
ENGINE_CALLS_TOTAL = Counter("engine_calls_total", "Total engine invocations")
ENGINE_CALL_ERRORS = Counter("engine_call_errors_total", "Total engine invocation errors")
ENGINE_CALL_DURATION = Histogram("engine_call_duration_seconds", "Engine call duration")

# Convenience decorator for timing

def timed(name: str):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            start = time.perf_counter()
            try:
                return fn(*args, **kwargs)
            finally:
                duration = (time.perf_counter() - start) * 1000
                logger.debug("perf| %s | %.2f ms", name, duration)
        return wrapper
    return decorator 