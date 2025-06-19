# Flow builder engine

# What is does at high level
The engine is a stateless traversal service (package name **`flow_engine`**) exposed via `/v1/api/next_question_flow`.  
Each call starts at the supplied **Section** and walks the graph until it finds the next unanswered **Question** or an **Action** that changes control-flow.  
All identifiers (`sectionId`, `questionId`, `actionId`) are resolved to the **latest active `*Version`** node so historic versions are ignored.


## Node types

### Track
The Track node is used in the builder similar to a 'Project' where multiple sections belong to a Track. For the engine it is not used.

### Section
A Section is the specific flow we will ask the engine to run.

Sample Section Payload (with variables)
```jsonc
{
  "sectionId": "SEC_PERSONAL_INFO",
  "name": "Personal Information",
  "stage": "Application",
  "description": "Collect basic personal details from the applicant",
  "x": 120,
  "y": 80,
  "zoom": 1.0,
  "showOnCanvas": true,
  "versionNumber": 5,
  "inputParams": ["applicationId", "applicantId"],
  "variables": [
    {
      "name": "application",
      "cypher": "MATCH (a:Application {applicationId:$applicationId}) RETURN a"
    }
  ]
}
```

### Question
A Question node holds all information about a question; the engine returns the **next unanswered** question once its incoming path is satisfied.

Sample Question Payload
```jsonc
{
  "questionId": "Q_AD_FIRST_NAME",
  "prompt": "What is your first name?",
  "fieldId": "F_AD_FIRST_NAME",
  "dataType": "string",
  "exampleAnswer": "Jane",
  "orderInForm": 10,
  "versionNumber": 3,
  "variables": [
    {
      "name": "first_name_dp",
      "cypher": "MATCH (d:Datapoint)-[:ANSWERS]->(q:Question {questionId:'Q_AD_FIRST_NAME'}) RETURN d"
    }
  ]
}
```


### Action
Actions contain either python code or CYPHER code that will be run on the server in order to create a new node, return in the payload the next section we should list questions for or mark a section as complete

#### Create a new node
The **CreatePropertyNode** action inserts new domain nodes (e.g. a `Property`) and usually returns the created IDs.

Sample Action Payload
```jsonc
{
  "actionId": "ACTION_CREATE_PROPERTY",
  "actionType": "CreatePropertyNode",
  "cypher": "MATCH (a:Applicant {applicantId: $applicantId}) CREATE (a)-[:HAS_PROPERTY]->(p:Property {address:$address}) RETURN id(p) AS createdId",
  "returns": { "createdNodeIds": "list<int>" },
  "variables": [
    {
      "name": "new_prop",
      "cypher": "MATCH (p:Property) WHERE id(p) = {{ createdNodeIds[0] }} RETURN p"
    }
  ]
}
```

#### Go to Next Section
The **GotoSection** action instructs the frontend to switch context to a new Section and re-invoke the engine, it will return in the payload .

Sample Action Payload – Goto Section
```jsonc
{
  "actionId": "ACTION_GOTO_SECTION",
  "actionType": "GotoSection",
  "nextSectionId": "SEC_ADDRESS_HISTORY",
  "props": { "applicantId": "$applicantId" },
  "variables": [
    {
      "name": "next_section_obj",
      "cypher": "MATCH (s:Section {sectionId:'SEC_ADDRESS_HISTORY'}) RETURN s"
    }
  ]
}
```

Sample Response Payload
```jsonc
{
  "sectionId": "SEC_PERSONAL_INFO",
  "question": { /* Question node */ } | null,
  "nextSectionId": "SEC_ADDRESS_HISTORY" | null,
  "createdNodeIds": [123, 456],
  "completed": false,
  "requestVariables": { // this is all params passed to the endpoint being returned as they were passed in
    "applicationId": "123",
    "applicantId": "456"
  }
}
```

#### Mark section as complete
The **MarkSectionComplete** action finalises the current section by persisting a `COMPLETED` relationship.

Sample Action Payload – Mark Section Complete
```jsonc
{
  "actionId": "ACTION_MARK_COMPLETE",
  "actionType": "MarkSectionComplete",
  "cypher": "MATCH (app:Application {applicationId:$applicationId}), (sec:Section {sectionId:$sectionId}) MERGE (app)-[:COMPLETED]->(sec)"
}
```

## Edge Types

### PRECEDES
The `PRECEDES` edge is the incoming edge type for a **Question**. It may contain an optional `askWhen` predicate that gates traversal.

Sample Json Payload
```jsonc
{
  "type": "PRECEDES",
  "fromId": "SEC_PERSONAL_INFO",
  "toId": "Q_AD_FIRST_NAME",
  "askWhen": "python: {{ first_name_dp.value }} is None",  // use variable
  "variables": "{\"requested_dp\":{\"cypher\":\"MATCH (d:Datapoint)-[:ANSWERS]->(q:Question {questionId:'Q_AD_FIRST_NAME'}) RETURN d\"}}",
  "sourceNode": "cypher: MATCH (app:Application {applicationId:$applicationId})-[:HAS_APPLICANT]->(a:Applicant {applicantId:$applicantId}) RETURN a",
   "cypher: MATCH (src)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q {questionId:'Q_AD_FIRST_NAME'}) RETURN d"
}
```


### TRIGGERS
The `TRIGGERS` edge is the incoming edge type for an **Action**. It usually connects a Question to an Action and can also be gated by `askWhen`.

Sample Json Payload
```jsonc
{
  "type": "TRIGGERS",
  "fromId": "Q_AD_ABN",
  "toId": "ACTION_CREATE_PROPERTY",
  "askWhen": "python: {{ first_name_dp.value }} is not None",
  "variables": "{}",  // none for this edge
   "cypher: MATCH (d:Datapoint {variableName:'abn_answer'}) RETURN d"
}
```

## Endpoint Description
**Path:** Endpoint path will be /v1/api/next_question_flow

**Payload** 
Example request payload

```json
{
    "sectionId" : "xxx",
    "applicationId" : "xxx",
    "applicantId" : "xxx"
}
```

## Runtime logic

**Step 1:** The client calls our endpoint with the relevant parameters in the request payload

**Step 2:** The engine will extract the properties from the payload for use in the flow

**Step 3:** Resolve the latest active `SectionVersion` node. Build a **context** object containing all `inputParams` (e.g. `applicationId`, `applicantId`), any properties returned by earlier actions, plus helper functions (e.g. `run_cypher`). These `inputParams` are also pre-loaded into the variable map so templates can reference them directly.  

**Step 4:** Recursive traversal
1. Enumerate outgoing edges from the current node (`PRECEDES` or `TRIGGERS`) ordered by `orderInForm` (fallback create-time).  
2. Evaluate each edge’s `askWhen` predicate (default **TRUE**). The predicate string can start with `cypher:` or `python:` to choose the evaluator.  
3. Select the *first* edge that returns **TRUE**. If none match, the traversal ends.
   * **Target = Question**  
     • Resolve `sourceNode` from the **sourceNode** field on the *PRECEDES* edge. This may be Cypher/Python or `{{ var }}` and is evaluated lazily.  
      • Use the resolved `sourceNode` to look for an existing `(:Datapoint)-[:ANSWERS]->(Question)` reachable via `sourceNode-[:SUPPLIES]->`.  
      • If the query returns a datapoint (non-null) → continue traversal.  
     • Else → stop and return this question to the client along with the `requestVariables` and `sourceNode`.
   * **Target = Action**  
     • Execute its body (Cypher or sandboxed Python).
      • Honour `returnImmediately` flag (default **true**). If **true** the engine stops traversal and returns:
        – The original `inputParams` payload
        – All variables resolved so far
        – Any `returns` defined on the Action
      • If `returnImmediately` is **false** → continue traversal after executing the action.  
     • Collect side-effects (`createdNodeIds`, `nextSectionId`, arbitrary `props`).  
     • If `nextSectionId` is returned → break traversal and include it in the response. Otherwise continue from the action’s outgoing edges.

**Step 5:** Produce response
```jsonc
{
  "sectionId": "SEC_PERSONAL_INFO",
  "question": { /* Question node */ } | null,
  "nextSectionId": "SEC_ADDRESS_HISTORY" | null,
  "createdNodeIds": [123, 456],
  "completed": false,
  "requestVariables": { /* variables passed to the endpoint */ },
  "sourceNode": { /* source node */ }
}
```
Sections are considered completed when the traversal reaches a **MarkSectionComplete** action or no further edges are available. The `MarkSectionComplete` action will create a `COMPLETED` relationship between the `source node` and `Section` nodes. We will have a query on the Action node that indicates how to find the `source node` using CYPHER/PYTHON/Variable.

---

## Context & Datapoint Scoping

The supplier node ("**source node**") is now declared explicitly instead of guessed from IDs:

* **Questions** – `sourceNode` lives on each inbound **PRECEDES** edge.
* **Actions and other nodes** – `sourceNode` is defined directly on the node itself. If omitted the engine reuses the most recently resolved `sourceNode`.

Evaluation flow:

1. Lazily evaluate `sourceNode` (Cypher, Python, or `{{ var }}`) and store the resulting node in `context.sourceNode`. The node is also exposed to templates via `{{ sourceNode }}`.
2. To determine if a Question is answered the engine runs a standard pattern match from the resolved `sourceNode`:
```cypher
MATCH (src)-[:SUPPLIES]->(d:Datapoint)-[:ANSWERS]->(q {questionId:$questionId}) RETURN d LIMIT 1
```
If no row is returned the question is considered unanswered.
3. If `null` the engine stops traversal and returns the Question along with `requestVariables` and the resolved `sourceNode`.
4. For Actions the same `sourceNode` is available for relationship mutations such as the `COMPLETED` link in **MarkSectionComplete**.

This explicit model supersedes the previous Applicant/Application heuristic and supports nested suppliers (e.g. `AddressHistory`) through expressive Cypher/Python definitions.

---

## Package Layout (`backend/flow_engine/`)

```text
flow_engine/
  __init__.py
  engine.py          # expose run_section(section_id, **ctx)
  evaluators.py      # cypher_eval(), python_eval()
  traversal.py       # graph walking helpers
  models.py          # Pydantic contracts mirroring docs here
  security.py        # sandbox utilities
  neo.py             # thin wrapper around neo4j-driver
  tests/
    fixtures.cypher
    test_engine.py
```

Install locally for development:

```bash
pip install -e backend/flow_engine
```

---

## Security & Sandboxing

| Surface  | Mitigation |
|----------|------------|
| Cypher   | Execute via dedicated `flow-engine` DB user with no restricted rights. |
| Python   | Run inside `RestrictedPython` environment. Allowed built-ins: `len`, `min`, `max`, `sum`, `sorted`, modules `re`, `datetime`. |
| Timeouts | Each evaluator capped at **1500 ms** (async timeout). |
| Logging  | All execution (query + params) logged to structured log for audit. Log should be a json object and will in future allow us to render a timeline of events in the same UI as the flow engine. |

Errors are returned with HTTP 409 and include `errorType`, `message`, and `traceId` for correlation.

---

## Testing Strategy

1. Load `tests/fixtures.cypher` into a disposable Neo4j instance (Docker) prior to test run.
2. Pytest parameterises calls to `run_section()` with different payloads to assert:
   * Next Question ID
   * Section completion flag
   * Side-effect node counts
3. CI (GitHub Actions) runs `pytest -q` on every PR.


---

## Variables

Variables are stored on the node/edge as **stringified JSON** under the `variables` property. The engine will `json.loads()` (Python) / `JSON.parse()` (JS tests) at runtime.  

Variables let earlier answers or computed values be reused later in the flow **without re-querying** Neo4j every time.

> **Note**: Every key listed in `inputParams` for the Section is automatically injected into the variable context at runtime. They behave exactly like user-defined variables and can be referenced with the same `{{ paramName }}` syntax (e.g. `{{ applicationId }}`, `{{ applicantId }}`). These parameters are **read-only**. A `variables` array can be attached to:

* `Section` nodes (global to the section)
* `PRECEDES` / `TRIGGERS` edges (local to the path)
* `Action` nodes (local to the action and its descendants)

### Schema
```jsonc
{
  "variables": [
    {
      "name": "q_first_name_1232",              // unique within the section
      "cypher": "MATCH (d:Datapoint)-[:ANSWERS]->(q:Question {questionId:'Q_AD_FIRST_NAME'}) WHERE d.variableName = $var RETURN d",
      "timeoutMs": 500                           // optional, default 500
    }
  ]
}
```

* `name` – identifier used in templates.
* `cypher` **or** `python` – exactly one evaluator string. Returned value may be a node/rel/map/list/scalar.
* `timeoutMs` – evaluator timeout; error if exceeded.

### Reference Syntax
We adopt **double-mustache** with dot notation, chosen because it is:
* Ignored by Cypher and Python parsers → safe to leave inside string literals.
* Easy to locate and replace before execution.

Examples:
* Cypher inside Action: `MATCH (a:Applicant {applicantId: {{ applicant.applicantId }} }) RETURN a`
* Python askWhen: `{{ q_first_name_1232.value }} is not None and len({{ q_first_name_1232.value }}) > 1`

During execution the engine replaces `{{ ... }}` with a JSON-encoded literal **before** sending the statement to the evaluator.

### Resolution Algorithm (lazy)
1. When the engine encounters a template placeholder, it checks `context.vars`:
   * **Hit** → substitute cached value.
   * **Miss** →
     1. Locate variable definition (`Section` → inbound edges → current node).
     2. Execute its evaluator with the current context (applicationId, applicantId, etc.).
     3. If result is a string that looks like JSON – attempt `json.loads` so nested props are accessible.
     4. Cache under `context.vars[name]`.
2. If evaluation throws or times out →
   * Set value to `null`.
   * Append warning to `response.warnings`.

### Accessing Properties
The value returned from the evaluator is exposed to templates as a Python‐like object supporting dot & bracket access. For Neo4j nodes we expose `.properties` as attributes.

### Response Extension
```jsonc
{
  "question": { /* … */ },
  "vars": {
    "q_first_name_1232": {
      "value": "Jane",           // example scalar
      "raw": { /* original */ }
    }
  },
  "warnings": [
    { "variable": "q_first_name_1232", "message": "Timeout – returned null" }
  ]
}
```

### Security Notes
* Variable evaluators run under the same sandbox rules as Action code.
* Each evaluator limited to `timeoutMs` and **100 rows** (configurable).
* All substitutions occur server-side; clients cannot inject arbitrary Cypher/Python.

---