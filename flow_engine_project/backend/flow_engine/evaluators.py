"""Evaluator utilities for Cypher and sandboxed Python execution.

These functions will be implemented in later tasks.
"""
from __future__ import annotations

from typing import Any, Dict, Optional
import json
import re

from loguru import logger

from .neo import run_cypher, neo_client
from .security import secure_eval_python
from .errors import EvaluatorTimeoutError

# Maximum rows to return from Cypher queries executed via evaluator
_ROW_CAP = 100

# Regex for double-mustache placeholders
_TMPL_RE = re.compile(r"\{\{\s*([\w\.]+)\s*\}\}")


def _json_parse_if_possible(value: Any) -> Any:
    """If *value* is a JSON string, return parsed object; else return original."""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    return value


def cypher_eval(statement: str, ctx: Dict[str, Any], timeout_ms: Optional[int] = None) -> Any:
    """Execute a Cypher statement safely.

    Enforces a **row cap** of 100 to mitigate data exfiltration risks. If more
    rows are returned a `ValueError` is raised.
    """
    # First substitute templates
    statement = _substitute_template(statement, ctx)

    # Strip optional "cypher:" prefix
    if statement.lstrip().lower().startswith("cypher:"):
        statement = statement.split(":", 1)[1].strip()

    logger.debug("Evaluating Cypher expression with ctx keys {}", list(ctx.keys()))

    # Strip private helper keys (e.g. "__ctx__") so we don't pass unsupported
    # Python objects (like the Context instance) to the Neo4j driver.
    safe_params = {k: v for k, v in ctx.items() if not k.startswith("__")}

    # Execute query – runtime timeout is currently handled at DB/driver level.
    with neo_client._driver.session() as _session:
        records = list(_session.run(statement, **safe_params))

    if len(records) > _ROW_CAP:
        raise ValueError(
            f"Cypher evaluation returned {len(records)} rows which exceeds the cap of {_ROW_CAP}."
        )

    # Return single value convenience if exactly one record & field
    if len(records) == 1 and len(records[0].keys()) == 1:
        return _json_parse_if_possible(records[0][0])

    # Attempt JSON parse for each record value
    parsed = []
    for rec in records:
        parsed.append({k: _json_parse_if_possible(v) for k, v in rec.items()})

    return parsed


def python_eval(code_str: str, ctx: Dict[str, Any], timeout_ms: Optional[int] = None) -> Any:
    """Evaluate Python code in sandbox with timeout protection."""

    # First substitute templates
    code_str = _substitute_template(code_str, ctx)

    # Strip optional prefix
    if code_str.lstrip().lower().startswith("python:"):
        code_str = code_str.split(":", 1)[1].strip()

    try:
        result = secure_eval_python(code_str, ctx, timeout_ms=timeout_ms)
        return _json_parse_if_possible(result)
    except EvaluatorTimeoutError:
        # Re-raise to callers; they may convert to warnings.
        raise
    except Exception as exc:  # pragma: no cover
        logger.exception("Python evaluator failed: {}", exc)
        raise


def _resolve_placeholder(expr: str, ctx: Dict[str, Any]):
    """Resolve a placeholder expression like `var.prop` against ctx."""

    parts = expr.split(".")

    # --------------------------------------------------------------
    # Step 1 – fetch the root variable (e.g. "applicant_age" in
    # "applicant_age.value").
    # --------------------------------------------------------------
    root_name = parts[0]

    val: Any = ctx.get(root_name)

    # --------------------------------------------------------------
    # Lazy-load: if the variable is *not* in the evaluator context but we
    # have access to the backing ``Context`` object, trigger
    # ``Context.resolve_var`` so that the variable definition (from Neo4j)
    # is executed on demand.
    # --------------------------------------------------------------
    if val is None and "__ctx__" in ctx:
        _ctx_obj = ctx["__ctx__"]
        try:
            # `resolve_var` gracefully handles unknown variables.
            val = _ctx_obj.resolve_var(root_name)  # type: ignore[attr-defined]
            # Store the freshly resolved value back into the evaluator ctx so
            # subsequent look-ups in the same substitution pass are fast.
            ctx[root_name] = val
        except Exception:  # pragma: no cover – resolution errors captured elsewhere
            val = None

    # --------------------------------------------------------------
    # Step 2 – drill down through properties if the placeholder contains dots
    # (e.g. ``variable.prop.subprop``)
    # --------------------------------------------------------------
    for part in parts[1:]:
        if val is None:
            break
        if isinstance(val, dict):
            val = val.get(part)
        else:
            val = getattr(val, part, None)

    return val


def _substitute_template(text: str, ctx: Dict[str, Any]) -> str:
    """Replace `{{ var }}` placeholders with JSON literals from ctx."""

    def _replace(match):
        expr = match.group(1)
        val = _resolve_placeholder(expr, ctx)
        json_literal = json.dumps(val)
        return json_literal

    return _TMPL_RE.sub(_replace, text) 