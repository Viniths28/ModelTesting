"""Thin wrapper around neo4j-driver sessions for the Flow Builder Engine.

This module provides both synchronous and asynchronous helpers and a retry
mechanism for transient errors (e.g. dead-locks).
"""

from __future__ import annotations

import os
from typing import Any, Dict, Callable, TypeVar, Awaitable

from loguru import logger
from neo4j import (
    AsyncGraphDatabase,
    GraphDatabase,
    basic_auth,
    exceptions as neo_exceptions,
)
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential_jitter,
    retry_if_exception_type,
)
from .logging import timed

# ---------------------------------------------------------------------------
# Environment configuration
# ---------------------------------------------------------------------------
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7689")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "testpassword")

# Retry policy constants
_MAX_ATTEMPTS = int(os.getenv("NEO4J_MAX_RETRIES", "3"))


# ---------------------------------------------------------------------------
# Retry decorator factory
# ---------------------------------------------------------------------------
RT = TypeVar("RT")


def _retry_on_transient(fn: Callable[..., RT]) -> Callable[..., RT]:
    """Apply exponential back-off retry for transient Neo4j errors."""

    transient_errors = (
        neo_exceptions.TransientError,
        neo_exceptions.ServiceUnavailable,
        neo_exceptions.SessionExpired,
    )

    @retry(
        reraise=True,
        stop=stop_after_attempt(_MAX_ATTEMPTS),
        wait=wait_exponential_jitter(initial=0.2, max=2.0),
        retry=retry_if_exception_type(transient_errors),
    )
    @timed("cypher_sync")
    def _wrapped(*args, **kwargs):  # type: ignore[override]
        return fn(*args, **kwargs)

    return _wrapped  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Synchronous client
# ---------------------------------------------------------------------------
class Neo4jClient:
    """Synchronous Neo4j helper with retry support."""

    def __init__(self) -> None:
        self._driver = GraphDatabase.driver(
            NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
        )

    def close(self) -> None:
        self._driver.close()

    @_retry_on_transient
    def run_cypher(self, statement: str, params: Dict[str, Any] | None = None):
        """Execute a Cypher query within a managed session."""
        params = params or {}
        logger.debug("Cypher| {} | {}", statement, params)
        with self._driver.session() as session:
            return session.run(statement, **params)


# ---------------------------------------------------------------------------
# Asynchronous client
# ---------------------------------------------------------------------------
class AsyncNeo4jClient:
    """Async variant using `AsyncGraphDatabase`."""

    def __init__(self) -> None:
        self._driver = AsyncGraphDatabase.driver(
            NEO4J_URI, auth=basic_auth(NEO4J_USER, NEO4J_PASSWORD)
        )

    async def close(self) -> None:  # pragma: no cover
        await self._driver.close()

    @_retry_on_transient  # type: ignore[misc]
    @timed("cypher_async")
    async def run_cypher_async(
        self, statement: str, params: Dict[str, Any] | None = None
    ):  # type: ignore[override]
        """Execute a Cypher query asynchronously within a managed session."""
        params = params or {}
        logger.debug("Cypher| {} | {}", statement, params)
        async with self._driver.session() as session:
            return await session.run(statement, **params)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------
# Singleton instances (can be swapped in tests)
neo_client = Neo4jClient()
async_neo_client = AsyncNeo4jClient()


def run_cypher(statement: str, params: Dict[str, Any] | None = None):
    """Convenience wrapper using the module-level sync client."""
    return neo_client.run_cypher(statement, params) 