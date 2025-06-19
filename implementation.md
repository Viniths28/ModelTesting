# Flow Builder Engine – Implementation Plan

Below is a step-by-step plan to implement the Flow Builder Engine described in `engine_build 1.md`. Each section contains a checklist so progress can be tracked easily.

---

## 1. Repository & Environment Setup
- [ ] Initialise Git repository and commit the existing specification docs
- [x] Add Python project scaffolding (`pyproject.toml` or `requirements.txt`)
- [x] Set up a `.env.example` file with Neo4j credentials and other secrets
- [x] Configure pre-commit hooks (black, isort, flake8, mypy)
- [x] Provide a `Makefile` / `tasks.py` for common dev commands (lint, test, run)

## 2. Core Package Structure (`backend/flow_engine/`)
- [x] Create directory tree as specified (`engine.py`, `evaluators.py`, `traversal.py`, `models.py`, `security.py`, `neo.py`, `tests/`)
- [x] Add `__init__.py` exporting `run_section()`
- [x] Write minimal stub implementations for each module so tests can import

## 3. Neo4j Integration Layer (`neo.py`)
- [x] Wrap neo4j-driver with helper to obtain async session/transaction
- [x] Implement retriable transaction decorator (back-off on deadlocks)
- [x] Expose `run_cypher(stmt, params)` utility used by evaluators & engine
- [ ] Add dedicated `flow-engine` DB user with restricted permissions

## 4. Data Models (`models.py`)
- [x] Define Pydantic classes for Section, Question, Action, Edge types
- [x] Encode variable schema, evaluator definitions, and response payload model
- [x] Include `Config` blocks to enable ORM-style attribute access for Neo4j nodes
- [x] Add version resolution logic for `*Version` nodes (latest active only)
- [x] Model specific Action types: `CreatePropertyNode`, `GotoSection`, `MarkSectionComplete`
- [x] Define Edge types: `PRECEDES` (with `askWhen`, `sourceNode`), `TRIGGERS`

## 5. Security & Sandboxing (`security.py`)
- [x] Integrate `RestrictedPython` with allowed built-ins/modules (`len`, `min`, `max`, `sum`, `sorted`)
- [x] Allow specific modules: `re`, `datetime`
- [x] Enforce execution timeout (1500 ms default, overridable per call)
- [x] Implement Cypher execution guard (limited user, row cap 100)
- [x] Provide helper `secure_eval_python(code_str, context)`

## 6. Evaluators (`evaluators.py`)
- [x] Implement `cypher_eval(statement, ctx, timeout_ms)` using `neo.run_cypher`
- [x] Implement `python_eval(code_str, ctx, timeout_ms)` via sandbox
- [x] Add automatic JSON parsing of string results
- [x] Support `cypher:` and `python:` prefixes for evaluator selection
- [x] Unit-test both evaluators with happy path & timeout cases

## 7. Traversal Helpers (`traversal.py`)
- [x] Implement graph walking algorithm outlined in spec (ordered edges, askWhen)
- [x] Support lazy variable resolution & caching via `context.vars`
- [x] Handle sourceNode resolution rules (PRECEDES edges vs node-level) – basic placeholder
- [x] Implement edge ordering by `orderInForm` (fallback create-time)
- [x] Support `askWhen` predicate evaluation (default TRUE)
- [x] Return structured result object (Question | Action | Complete)

## 8. Engine Facade (`engine.py`)
- [x] Implement `run_section(section_id, **input_params)` high-level function
- [x] Resolve latest active `SectionVersion` node
- [x] Build initial `Context` (inputParams, helper fns, empty vars dict)
- [x] Pre-load `inputParams` into variable map for template reference (via Context)
- [x] Call traversal helpers and post-process response (warnings, flags)
- [x] Expose engine for import by API layer & tests

## 9. Datapoint & Source Node Logic
- [x] Implement explicit `sourceNode` resolution from PRECEDES edges
- [x] Support `sourceNode` fallback from most recently resolved node
- [x] Add standard datapoint query for answered check
- [x] Expose `sourceNode` to templates via `{{ sourceNode }}` (via evaluator_ctx)
- [x] Handle unanswered vs answered question detection

## 10. Actions Implementation
- [x] Implement support for `CreatePropertyNode`, `GotoSection`, `MarkSectionComplete`
- [x] Honour `returnImmediately` flag behaviour (default true) – note: non-immediate continuation not yet supported
- [x] Surface side-effects in engine response (`createdNodeIds`, `nextSectionId`)
- [x] Support Action-level `variables` and `sourceNode` definitions (basic)
- [x] Handle `returns` schema for CreatePropertyNode actions (basic collection)
- [x] Implement `COMPLETED` relationship creation for MarkSectionComplete

## 11. Variable System
- [x] Implement variable lookup algorithm (basic: inputParams + cache) 
- [x] Add template substitution using double-mustache `{{ var }}`
- [x] Support dot notation for property access (`{{ var.property }}`)
- [x] Cache evaluated variables in context (stub)
- [x] Auto-inject `inputParams` as read-only variables
- [x] Provide null result & warning handling on error/timeout (warnings placeholder)
- [x] Support variables on Section nodes, PRECEDES/TRIGGERS edges, Action nodes
- [x] Implement `timeoutMs` per variable (default 500ms)

## 12. Response Format Implementation
- [x] Return structured response matching specification (sectionId, question, nextSectionId, createdNodeIds, completed, requestVariables, sourceNode)
- [x] Include `vars` object with evaluated variables
- [x] Add `warnings` array for evaluation errors

## 13. API Layer (`backend/app.py`)
- [x] Choose FastAPI (or Flask) and create `/v1/api/next_question_flow` route
- [x] Validate request payload against Pydantic model
- [x] Pass parameters to `flow_engine.run_section()`
- [x] Marshal engine response to JSON and return HTTP 200
- [x] Handle engine errors → HTTP 409 with `errorType`, `message`, `traceId`

## 14. Logging & Observability
- [x] Configure structured JSON logging (loguru) across modules
- [x] Log all Cypher/Python executions with params & duration
- [x] Generate `traceId` per request and propagate through engine layers
- [x] Create audit timeline placeholder via JSON logs
- [x] Integrate simple timing & count metrics (Prometheus exporter)

## 15. Error Handling Strategy
- [x] Define custom exceptions (`FlowError`, `EvaluatorTimeoutError`, `SecurityError`, `SectionNotFoundError`)
- [x] Map exceptions to HTTP status codes in API layer (409 domain, 500 unexpected)
- [x] Ensure meaningful messages plus `traceId` are returned to clients
- [x] Handle version resolution failures gracefully

## 16. Testing (`tests/`)
- [x] Write Neo4j fixture import (`fixtures.cypher`)
- [x] Add Pytest unit tests for evaluators, traversal, engine end-to-end
- [x] Parameterise tests to cover unanswered vs answered question paths
- [x] Test specific scenarios: Next Question ID, Section completion flag, Side-effect node counts (implicit row cap, sandbox)
- [x] Include security regression tests (restricted built-ins, row limits)
- [x] Test variable resolution, template substitution, timeout handling


---

*Last updated: <!-- YYYY-MM-DD -->* 