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
from .errors import EvaluatorTimeoutError, FlowError

try:
    from neo4j.graph import Node, Relationship, Path  # type: ignore
except ImportError:
    Node = Relationship = Path = None  # type: ignore

# Maximum rows to return from Cypher queries executed via evaluator
_ROW_CAP = 100

# Regex for double-mustache placeholders
_TMPL_RE = re.compile(r"\{\{\s*([\w\.]+)\s*\}\}")


def _json_parse_if_possible(value: Any) -> Any:
    """
    If *value* is a JSON string, return parsed object; else return original.
    
    NOTE: We do NOT convert Neo4j objects here anymore, as that breaks
    internal processing that expects Node objects. Neo4j object handling
    is now done only in _to_json_safe for final serialization.
    """
    # Original JSON parsing logic only
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (ValueError, TypeError):
            return value
    
    return value


def _normalize_cypher_quotes(cypher_query: str) -> str:
    """
    Normalize single quotes to double quotes in Cypher string literals.
    
    This allows JSON payloads to use single quotes (easier to write/read) while
    ensuring Cypher receives properly formatted double-quoted string literals.
    
    Examples:
        {type:'CO_APPLICANT'} -> {type:"CO_APPLICANT"}
        'Q_AD_Number_of_Applicants' -> "Q_AD_Number_of_Applicants"
        'No' -> "No"
    """
    # Pattern to match Cypher string literals with single quotes
    # This matches single-quoted strings that are likely to be Cypher string literals
    # Handles: property values, string literals in comparisons, etc.
    
    # Match single-quoted strings, being careful to avoid issues with escaped quotes
    pattern = r"'([^'\\]*(\\.[^'\\]*)*?)'"
    
    def replace_quotes(match):
        # Extract the content between single quotes
        content = match.group(1)
        # Return the same content wrapped in double quotes
        return f'"{content}"'
    
    normalized = re.sub(pattern, replace_quotes, cypher_query)
    
    # Log the normalization if changes were made
    if normalized != cypher_query:
        logger.debug("Normalized Cypher quotes: {} -> {}", 
                    cypher_query[:100] + "..." if len(cypher_query) > 100 else cypher_query,
                    normalized[:100] + "..." if len(normalized) > 100 else normalized)
    
    return normalized


def cypher_eval(statement: str, ctx: Dict[str, Any], timeout_ms: Optional[int] = None) -> Any:
    """Execute a Cypher statement safely.

    Enforces a **row cap** of 100 to mitigate data exfiltration risks. If more
    rows are returned a `ValueError` is raised.
    """
    # Guard: ensure we actually received a textual Cypher snippet – helps diagnose
    if not isinstance(statement, str):
        raise FlowError(
            f"Cypher evaluator expected a string but received {type(statement).__name__}: {statement!r}"
        )

    # First substitute templates
    statement = _substitute_template(statement, ctx, python_mode=False)

    # Strip optional "cypher:" prefix
    if statement.lstrip().lower().startswith("cypher:"):
        statement = statement.split(":", 1)[1].strip()

    # NEW: Normalize single quotes to double quotes for Cypher compatibility
    statement = _normalize_cypher_quotes(statement)

    logger.debug("Evaluating Cypher expression with ctx keys {}", list(ctx.keys()))

    # Strip private helper keys (e.g. "__ctx__") and Neo4j objects so we don't pass 
    # unsupported Python objects to the Neo4j driver.
    safe_params = {}
    for k, v in ctx.items():
        if k.startswith("__"):
            continue  # Skip private helper keys
        
        # Skip Neo4j objects that can't be serialized as query parameters
        if Node is not None and isinstance(v, Node):
            continue
        if Relationship is not None and isinstance(v, Relationship):
            continue
        if Path is not None and isinstance(v, Path):
            continue
        if hasattr(v, '__class__') and 'neo4j' in str(type(v)):
            continue
            
        safe_params[k] = v

    # Execute query – runtime timeout is currently handled at DB/driver level.
    with neo_client._driver.session() as _session:
        records = list(_session.run(statement, **safe_params))

    if len(records) > _ROW_CAP:
        raise ValueError(
            f"Cypher evaluation returned {len(records)} rows which exceeds the cap of {_ROW_CAP}."
        )

    # Enhanced single value extraction logic
    if len(records) == 1:
        record = records[0]
        keys = record.keys()
        
        # Case 1: Single unnamed field - return the raw value
        if len(keys) == 1:
            result = _json_parse_if_possible(record[0])
            logger.debug("Cypher eval: Single field result -> {}", type(result).__name__)
            return result
        
        # Case 2: Multiple fields but contains 'value' field - prioritize 'value'
        elif "value" in keys:
            result = _json_parse_if_possible(record["value"])
            logger.debug("Cypher eval: Extracted 'value' field -> {}", type(result).__name__)
            return result
        
        # Case 3: Multiple fields, no 'value' field - return full record
        else:
            result = {k: _json_parse_if_possible(v) for k, v in record.items()}
            logger.debug("Cypher eval: Multiple fields, returning full record with keys: {}", list(keys))
            return result
    
    # Multiple records - return array of processed records
    parsed = []
    for rec in records:
        # For each record, apply the same logic as single record case
        keys = rec.keys()
        if len(keys) == 1:
            # Single field - extract the value
            parsed.append(_json_parse_if_possible(rec[0]))
        elif "value" in keys:
            # Multiple fields with 'value' - prioritize 'value'
            parsed.append(_json_parse_if_possible(rec["value"]))
        else:
            # Multiple fields without 'value' - return full record
            parsed.append({k: _json_parse_if_possible(v) for k, v in rec.items()})

    return parsed


def python_eval(code_str: str, ctx: Dict[str, Any], timeout_ms: Optional[int] = None) -> Any:
    """Evaluate Python code in sandbox with timeout protection."""

    # Guard: ensure snippet is a string for RestrictedPython
    if not isinstance(code_str, str):
        raise FlowError(
            f"Python evaluator expected a string but received {type(code_str).__name__}: {code_str!r}"
        )

    # First substitute templates – python_mode ensures str values use repr()
    code_str = _substitute_template(code_str, ctx, python_mode=True)

    # Strip optional prefix
    if code_str.lstrip().lower().startswith("python:"):
        code_str = code_str.split(":", 1)[1].strip()

    # Debug: log final expression executed by RestrictedPython sandbox
    logger.info("Sandbox exec: {}", code_str)

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


def _to_json_safe(val: Any):
    """Convert values (including Neo4j types) into JSON-serialisable primitives."""
    if isinstance(val, (str, int, float, bool)) or val is None:
        return val

    # Handle Neo4j graph objects properly
    if Node is not None and isinstance(val, Node):
        return dict(val)
    
    if Relationship is not None and isinstance(val, Relationship):
        return {
            "type": val.type,
            "start": val.start_node.element_id if hasattr(val.start_node, 'element_id') else str(val.start_node.id),
            "end": val.end_node.element_id if hasattr(val.end_node, 'element_id') else str(val.end_node.id),
            "properties": dict(val)
        }
    
    if Path is not None and isinstance(val, Path):
        return [n.element_id if hasattr(n, 'element_id') else str(n.id) for n in val.nodes]

    # Handle other potential Neo4j types
    if hasattr(val, '__class__') and 'neo4j' in str(type(val)):
        logger.warning("Converting unknown Neo4j type {} to string in _to_json_safe: {}", type(val).__name__, str(val))
        return str(val)

    # Handle collections recursively
    if isinstance(val, (list, tuple, set)):
        return [_to_json_safe(v) for v in val]
    if isinstance(val, dict):
        return {k: _to_json_safe(v) for k, v in val.items()}

    # Fallback to string representation
    return str(val)


def _substitute_template(text: str, ctx: Dict[str, Any], *, python_mode: bool = False) -> str:
    """Replace `{{ var }}` placeholders.

    When *python_mode* is True we serialise plain strings using ``repr`` so that
    the resulting placeholder becomes a valid Python literal **without** the
    extra JSON-style double quotes. For all other data types we fall back to
    ``json.dumps`` so numbers, dicts, lists etc. remain valid literals in both
    Python and Cypher contexts.
    """

    def _replace(match):
        expr = match.group(1)
        val = _resolve_placeholder(expr, ctx)

        # For Python expressions we prefer repr() for primitive types so that
        #   strings → 'Yes'
        #   booleans → True / False (capitalised)
        #   None     → None
        # which are valid Python literals.
        if python_mode and isinstance(val, (str, bool, int, float, type(None))):
            return repr(val)

        try:
            json_literal = json.dumps(_to_json_safe(val))
        except TypeError:
            # Fallback: stringify value entirely
            json_literal = json.dumps(str(val))
        return json_literal

    return _TMPL_RE.sub(_replace, text) 