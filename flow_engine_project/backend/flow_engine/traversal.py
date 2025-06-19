"""Graph traversal helpers.

This module implements the recursive traversal algorithm described in
`engine_build 1.md`. The current implementation supports the basics of:

* Ordering edges by `orderInForm` (fallback create-time)
* askWhen predicate evaluation (supports `python:` and `cypher:`)
* Variable caching (lazy evaluation)
* Source node resolution for PRECEDES edges

The algorithm will be extended in later tasks to cover full Action handling,
variable scoping on edges/nodes, and section completion detection.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union
import re  # NEW: needed for placeholder detection

from loguru import logger

from .evaluators import cypher_eval, python_eval
from .models import EdgeType, EngineResponse, ActionType
from .neo import run_cypher, neo_client

# ---------------------------------------------------------------------------
# Context object
# ---------------------------------------------------------------------------


@dataclass
class Context:
    """Execution context shared during traversal."""

    input_params: Dict[str, Any]
    vars: Dict[str, Any] = field(default_factory=dict)
    source_node: Optional[Any] = None  # Neo4j node (dict-like)
    var_defs: Dict[str, Dict[str, Any]] = field(default_factory=dict)  # name -> def
    warnings: List[Dict[str, str]] = field(default_factory=list)

    # Helper to resolve a template variable lazily – *placeholder* implementation.
    def resolve_var(self, name: str) -> Any:  # noqa: D401
        if name in self.vars:
            return self.vars[name]
        var_def = self.var_defs.get(name)
        if not var_def:
            self.vars[name] = None
            return None

        evaluator_str = var_def.get("cypher") or var_def.get("python")
        timeout_ms = var_def.get("timeoutMs", 500)
        if not evaluator_str:
            self.vars[name] = None
            return None

        try:
            if evaluator_str.lower().startswith("cypher:") or var_def.get("cypher"):
                res = cypher_eval(evaluator_str, self.evaluator_ctx, timeout_ms=timeout_ms)
            else:
                res = python_eval(evaluator_str, self.evaluator_ctx, timeout_ms=timeout_ms)
        except Exception as exc:
            self.warnings.append({"variable": name, "message": str(exc)})
            res = None

        self.vars[name] = res
        return res

    # Helper to expose sourceNode to template evaluators via input_params
    @property
    def evaluator_ctx(self) -> Dict[str, Any]:
        # Expose a reference to the Context itself under a private key so that
        # template substitution can lazily resolve not-yet-evaluated variables
        # via ``Context.resolve_var`` without changing call signatures across
        # the codebase.  The key is prefixed with double underscores to avoid
        # clashing with legitimate variable names defined by users.
        return {
            **self.input_params,
            "sourceNode": self.source_node,
            **self.vars,
            "__ctx__": self,  # private backlink for lazy variable loading
        }


# ---------------------------------------------------------------------------
# askWhen evaluation
# ---------------------------------------------------------------------------

def _evaluate_ask_when(expr: Optional[str], ctx: Context) -> bool:
    """Return True if *expr* is truthy or None (default TRUE)."""

    if not expr:
        return True

    expr = expr.strip()

    try:
        if expr.lower().startswith("python:"):
            return bool(python_eval(expr, ctx.evaluator_ctx))
        if expr.lower().startswith("cypher:"):
            return bool(cypher_eval(expr, ctx.evaluator_ctx))
        # Default to python evaluator if no prefix
        return bool(python_eval(expr, ctx.evaluator_ctx))
    except Exception as exc:  # pragma: no cover
        logger.warning("askWhen evaluation errored → treating as FALSE: {}", exc)
        return False


# ---------------------------------------------------------------------------
# Neo4j helper queries
# ---------------------------------------------------------------------------

def _fetch_outgoing_edges(section_id: str) -> List[Tuple[dict, dict]]:
    """Return raw (edge, target_node) rows ordered as per spec."""

    cypher = (
        """
        MATCH (s:Section {sectionId:$sectionId})-[e]->(t)
        WHERE type(e) IN ['PRECEDES','TRIGGERS']
        RETURN e, t
        ORDER BY coalesce(e.orderInForm, e.order), id(e)
        """
    )
    result = run_cypher(cypher, {"sectionId": section_id})
    return [(rec["e"], rec["t"]) for rec in result]


# ---------------------------------------------------------------------------
# Source node resolution & answered check
# ---------------------------------------------------------------------------

def _resolve_source_node(edge_rel, ctx: Context) -> Optional[Any]:  # type: ignore[return-type]
    """Determine sourceNode for the given edge and update context."""

    src_expr = edge_rel.get("sourceNode")  # type: ignore[index]

    if src_expr:
        src_expr = src_expr.strip()
        try:
            if src_expr.lower().startswith("cypher:"):
                node = cypher_eval(src_expr, ctx.evaluator_ctx)
            elif src_expr.lower().startswith("python:"):
                node = python_eval(src_expr, ctx.evaluator_ctx)
            else:
                # ------------------------------------------------------------------
                # NEW: Support variable placeholder syntax e.g. '{{ current_applicant }}'
                # ------------------------------------------------------------------
                _tmpl_re = re.compile(r"\{\{\s*([\w\.]+)\s*\}\}")
                match = _tmpl_re.fullmatch(src_expr)
                if match:
                    var_name = match.group(1).split(".")[0]  # root variable name
                    node = ctx.resolve_var(var_name)
                else:
                    node = None
        except Exception as exc:  # pragma: no cover
            logger.warning("Failed to resolve sourceNode: {}", exc)
            node = None
    else:
        node = ctx.source_node  # fallback

    # Update context for child edges
    ctx.source_node = node
    return node


def _question_answered(source_node, question_id: str) -> bool:
    """Return True if a Datapoint exists that answers *question_id*."""

    if source_node is None:
        return False

    try:
        src_id = source_node.id  # type: ignore[attr-defined]
    except AttributeError:
        return False

    cypher = (
        """
        MATCH (src)
        WHERE id(src) = $srcId
        MATCH (src)-[:SUPPLIES]->(:Datapoint)-[:ANSWERS]->(q {questionId:$qid})
        RETURN q LIMIT 1
        """
    )
    with neo_client._driver.session() as _session:
        record = _session.run(cypher, srcId=src_id, qid=question_id).single()
    return record is not None


# ---------------------------------------------------------------------------
# Action execution helpers
# ---------------------------------------------------------------------------

def _resolve_action_source_node(action_node, ctx: Context) -> None:
    """If the Action node defines its own `sourceNode`, evaluate it."""

    src_expr = action_node.get("sourceNode")  # type: ignore[index]
    if not src_expr:
        return  # keep existing ctx.source_node

    try:
        if src_expr.lower().startswith("cypher:"):
            ctx.source_node = cypher_eval(src_expr, ctx.evaluator_ctx)
        elif src_expr.lower().startswith("python:"):
            ctx.source_node = python_eval(src_expr, ctx.evaluator_ctx)
    except Exception as exc:  # pragma: no cover
        logger.warning("Failed to resolve action sourceNode: {}", exc)


def _execute_action(action_node, ctx: Context) -> Dict[str, Any]:
    """Execute action node and return EngineResponse dict."""

    _resolve_action_source_node(action_node, ctx)

    action_type = action_node.get("actionType")  # type: ignore[index]
    return_immediately = action_node.get("returnImmediately", True)  # type: ignore[index]

    # Defaults
    next_section_id: Optional[str] = None
    created_ids: List[int] = []
    completed_flag = False

    if action_type == ActionType.CREATE_PROPERTY_NODE.value:
        cypher = action_node.get("cypher")  # type: ignore[index]
        if cypher:
            with neo_client._driver.session() as _session:
                records = _session.run(cypher, **ctx.evaluator_ctx).values()
            # Collect any integer IDs returned in first column by convention
            created_ids = [row[0] for row in records if row]

    elif action_type == ActionType.GOTO_SECTION.value:
        next_section_id = action_node.get("nextSectionId")  # type: ignore[index]

    elif action_type == ActionType.MARK_SECTION_COMPLETE.value:
        cypher = action_node.get("cypher")  # type: ignore[index]
        if cypher:
            run_cypher(cypher, ctx.evaluator_ctx)
        completed_flag = True

    else:
        logger.warning("Unknown action type {} – ignored", action_type)

    response = EngineResponse(
        sectionId=ctx.input_params.get("sectionId", ""),
        question=None,
        nextSectionId=next_section_id,
        createdNodeIds=created_ids,
        completed=completed_flag,
        requestVariables=ctx.input_params,
        sourceNode=ctx.source_node.id if ctx.source_node else None,
        vars={name: {"value": val} for name, val in ctx.vars.items()},
        warnings=ctx.warnings,
    ).dict()

    # If returnImmediately is False we could continue traversal (not yet supported)
    return response


# ---------------------------------------------------------------------------
# Variable definitions loading
# ---------------------------------------------------------------------------

def _load_section_vars(section_id: str) -> Dict[str, Dict[str, Any]]:
    cypher = "MATCH (s:Section {sectionId:$sid}) RETURN s.variables AS vars"  # variables is JSON string

    with neo_client._driver.session() as _session:
        rec = _session.run(cypher, sid=section_id).single()

    if rec is None:
        return {}

    raw = rec["vars"]
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except Exception:
        return {}
    return {v["name"]: v for v in parsed}


# ---------------------------------------------------------------------------
# Utility: fetch edges for arbitrary node
# ---------------------------------------------------------------------------

def _fetch_outgoing_edges_for_node(node_id: int) -> List[Tuple[dict, dict]]:
    """Return (edge, target_node) tuples for *node_id* ordered as per spec."""

    cypher = (
        """
        MATCH (n) WHERE id(n) = $nid
        MATCH (n)-[e]->(t)
        WHERE type(e) IN ['PRECEDES','TRIGGERS']
        RETURN e, t
        ORDER BY coalesce(e.orderInForm, e.order), id(e)
        """
    )

    with neo_client._driver.session() as _session:
        result = _session.run(cypher, nid=node_id)
        return [(r["e"], r["t"]) for r in result]


# ---------------------------------------------------------------------------
# Recursive traversal implementation
# ---------------------------------------------------------------------------

def _traverse(current_node, ctx: Context, section_id: str) -> Dict[str, Any]:
    """Depth-first traversal starting from *current_node* (Section/Question/Action)."""

    for edge_rel, target_node in _fetch_outgoing_edges_for_node(current_node.id):  # type: ignore[attr-defined]
        edge_type = edge_rel.type  # PRECEDES / TRIGGERS
        ask_when = edge_rel.get("askWhen")  # type: ignore[index]

        # Merge edge-level variable defs
        if edge_rel.get("variables"):
            try:
                edge_vars = json.loads(edge_rel["variables"])
                ctx.var_defs.update({v["name"]: v for v in edge_vars})
            except Exception:
                pass

        # Resolve and propagate sourceNode
        _resolve_source_node(edge_rel, ctx)

        # Evaluate askWhen predicate
        if not _evaluate_ask_when(ask_when, ctx):
            continue

        # --------------------------------------------------------------
        # Target is Question
        # --------------------------------------------------------------
        if edge_type == EdgeType.PRECEDES.value and target_node.labels.intersection({"Question"}):  # type: ignore[attr-defined]
            question_id = target_node["questionId"]  # type: ignore[index]

            if _question_answered(ctx.source_node, question_id):
                logger.debug("Question {} already answered – delve deeper", question_id)
                # Recurse into this question to follow its outgoing edges
                return _traverse(target_node, ctx, section_id)

            logger.debug("Stopping traversal – next unanswered question {}", question_id)
            return EngineResponse(
                sectionId=section_id,
                question={"questionId": question_id},
                nextSectionId=None,
                completed=False,
                createdNodeIds=[],
                requestVariables=ctx.input_params,
                sourceNode=ctx.source_node.id if ctx.source_node else None,
                vars={name: {"value": val} for name, val in ctx.vars.items()},
                warnings=ctx.warnings,
            ).dict()

        # --------------------------------------------------------------
        # Target is Action
        # --------------------------------------------------------------
        if "actionType" in target_node:
            logger.debug("Executing action {}", target_node["actionId"])
            return _execute_action(target_node, ctx)

    # No edges matched → completed
    logger.debug("Node {} completed – no further edges", current_node)
    return EngineResponse(
        sectionId=section_id,
        question=None,
        nextSectionId=None,
        completed=True,
        createdNodeIds=[],
        requestVariables=ctx.input_params,
        sourceNode=ctx.source_node.id if ctx.source_node else None,
        vars={name: {"value": val} for name, val in ctx.vars.items()},
        warnings=ctx.warnings,
    ).dict()


# ---------------------------------------------------------------------------
# Traversal entry-point (public)
# ---------------------------------------------------------------------------

def walk_section(start_section_id: str, ctx_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Traverse a Section recursively until next unanswered question or control-flow change."""

    # Fetch the Section node object safely within a managed session so the
    # result is consumed before the session closes.
    with neo_client._driver.session() as _session:
        record = _session.run(
            "MATCH (s:Section {sectionId:$sid}) RETURN s LIMIT 1",
            sid=start_section_id,
        ).single()

    if record is None:
        raise ValueError(f"Section '{start_section_id}' not found")

    section_node = record["s"]

    ctx = Context(input_params=ctx_dict)
    ctx.var_defs.update(_load_section_vars(start_section_id))

    return _traverse(section_node, ctx, start_section_id) 