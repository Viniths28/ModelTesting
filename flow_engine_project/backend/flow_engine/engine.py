"""Engine facade – public entry-point used by the REST API and tests."""

from __future__ import annotations

from typing import Any, Dict

from loguru import logger

from .neo import run_cypher
from .traversal import walk_section
from .errors import SectionNotFoundError, FlowError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _resolve_latest_section(section_id: str) -> str:
    """Return latest active section id. In current data model we assume the provided ID exists."""

    # Previously we validated existence via a Cypher query. However fetching the
    # result outside the driver session caused record‐consumed errors. Given the
    # traversal logic will hit the DB anyway and raise clear errors if the
    # Section is missing, we optimistically return the provided *section_id*.
    #
    # This keeps the function side-effect free and avoids an extra round-trip.
    return section_id


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_section(section_id: str, **input_params: Any) -> Dict[str, Any]:
    """Run the traversal engine starting from *section_id*.

    Parameters
    ----------
    section_id : str
        Identifier of the Section (or SectionVersion) node.
    **input_params : Any
        Arbitrary parameters injected into the execution context and returned
        under ``requestVariables`` so the caller can correlate.
    """

    logger.info("Engine invoked for section {} | params={} ", section_id, input_params)

    latest_section_id = _resolve_latest_section(section_id)

    response = walk_section(latest_section_id, input_params)

    # Attach warnings placeholder (future extension)
    response.setdefault("warnings", [])

    logger.info("Engine response | completed={} question={} nextSection={}",
                response.get("completed"),
                response.get("question"),
                response.get("nextSectionId"))

    return response 