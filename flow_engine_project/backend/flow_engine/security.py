"""Security and sandbox utilities.

This module integrates RestrictedPython and provides helper functions for
executing untrusted Python snippets under strict constraints.
"""

from __future__ import annotations

import concurrent.futures as _futures
import datetime as _datetime
import re as _re
import types
from typing import Any, Dict, Optional

from loguru import logger
from RestrictedPython import compile_restricted_eval
from RestrictedPython.Guards import safe_builtins as _safe_builtins

from .errors import EvaluatorTimeoutError, SecurityError

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
_DEFAULT_TIMEOUT_MS = 1500  # 1.5 seconds
_ALLOWED_BUILTINS = {
    "len": len,
    "min": min,
    "max": max,
    "sum": sum,
    "sorted": sorted,
}

_ALLOWED_MODULES = {
    "re": _re,
    "datetime": _datetime,
}

# Merge allowed builtins into the RestrictedPython default set
_builtins: Dict[str, Any] = dict(_safe_builtins)  # type: ignore[arg-type]
_builtins.update(_ALLOWED_BUILTINS)


# ---------------------------------------------------------------------------
# Core helper
# ---------------------------------------------------------------------------

def secure_eval_python(
    code_str: str,
    ctx: Dict[str, Any],
    timeout_ms: Optional[int] = None,
) -> Any:
    """Safely evaluate *code_str* inside RestrictedPython.

    Parameters
    ----------
    code_str : str
        The Python expression to evaluate. Should *not* include a leading
        ``python:`` prefix (strip that before calling).
    ctx : Dict[str, Any]
        Execution context – exposed as globals inside the sandbox.
    timeout_ms : int | None
        Maximum execution time in milliseconds (default 1500ms).

    Returns
    -------
    Any
        Evaluation result.

    Raises
    ------
    Exception
        Any exception raised by the sandboxed code itself.
    """

    timeout_ms = timeout_ms or _DEFAULT_TIMEOUT_MS

    def _evaluate() -> Any:
        # Compile expression – we only allow *expressions*, not full statements.
        compiled = compile_restricted_eval(code_str)
        # Handle RestrictedPython versions that return tuple
        if isinstance(compiled, tuple):
            compiled = compiled[0]  # first item is the compiled code object
        logger.debug("RestrictedPython compiled type: {}", type(compiled))
        globals_dict = {
            "__builtins__": _builtins,
            **_ALLOWED_MODULES,
            **ctx,
        }
        return eval(compiled, globals_dict)  # pylint: disable=eval-used

    with _futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(_evaluate)
        try:
            return future.result(timeout=timeout_ms / 1000.0)
        except _futures.TimeoutError as exc:  # pragma: no cover
            logger.warning("Python evaluator timed out after {} ms", timeout_ms)
            raise EvaluatorTimeoutError("Python evaluation timed out") from exc 