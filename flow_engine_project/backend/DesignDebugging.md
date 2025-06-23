
# Flow Engine Debugging Interface - Design Brief

Based on my analysis of your track (trackId: `30a48d44-db1c-4f91-b260-e52fa8c040f6`), I've traced through the complete flow structure and understand the execution patterns. Here's my comprehensive design for the debugging interface:

## Research Findings

Your track contains:
- **2 Sections**: "Get a Quote" and "Living Situation"
- **5 Actions**: Create Node (co-applicant), Complete Section, Go to Section, Create Node (address history), Complete Section  
- **6 Questions**: Connected via PRECEDES/TRIGGERS edges with complex askWhen conditions
- **Complex Variables**: Section-level, edge-level, and action-level variable definitions with Cypher/Python evaluation
- **Dynamic Flow Control**: Multiple conditional paths based on data availability and askWhen predicates

## Interface Architecture

### **Layout Structure**
```
┌─────────────┬─────────────────────────────────────┬─────────────────┐
│             │                                     │                 │
│  Left Panel │           Main Canvas               │   Right Panel   │
│  (300px)    │           (flex)                    │    (350px)      │
│             │                                     │                 │
│  Track      │  Flow Execution Visualization       │  Variables &    │
│  Browser    │                                     │  Debugging      │
│             │                                     │                 │
├─────────────┴─────────────────────────────────────┴─────────────────┤
│                     Bottom Panel (300px)                           │
│               JSON Editor & Execution Controls                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Left Panel - Track Browser

**Track Navigation Tree:**
- Expandable track list with chevron icons
- Each track shows sections as dropdown items
- **Browser Storage**: Selected track/section stored in `localStorage`
- **Auto-expand**: Previously selected track opens on page refresh
- **Visual Indicators**: 
  - 🔵 Recently executed sections
  - ⚪ Available sections
  - 🔴 Sections with errors

```
📁 ModelTesting
  ├── 📋 Get a Quote (SEC_0f962e4d...)
  └── 📋 Living Situation (SEC_1a879403...)
```

## Main Canvas - Flow Execution Visualization

**Dynamic Flow Graph Display:**
Based on my analysis of your flow, the visualization will show:

### **Node Types with Custom Styling:**
1. **Section Nodes** (Blue rectangles)
   - Section name + sectionId
   - Variable count badge
   - Source node indicator

2. **Question Nodes** (Yellow circles) 
   - Question ID
   - Answered status (✅ answered, ❓ unanswered, ⏳ stopped here)
   - askWhen condition preview

3. **Action Nodes** (Green hexagons)
   - Action type + actionId
   - Execution status (✅ executed, ⏭️ skipped, ❌ error)
   - Created node counts

### **Edge Visualization:**
- **PRECEDES edges**: Solid blue arrows
- **TRIGGERS edges**: Dashed green arrows  
- **askWhen conditions**: Shown as edge labels with evaluation result
- **Variable dependencies**: Dotted lines showing variable resolution flow

### **Execution Timeline:**
- **Execution Order**: Numbered badges (1, 2, 3...) showing traversal sequence
- **Current Position**: Highlighted node showing where execution stopped
- **Path Highlighting**: Executed path in bold colors, potential paths in muted colors
- **Timing Info**: Hover to see execution duration for each step

### **Interactive Features:**
- **Click nodes**: Expand to show full details
- **Hover edges**: Preview askWhen conditions and their evaluation
- **Zoom/Pan**: Handle complex flows with many nodes
- **Filtering**: Hide/show different node types

## Right Panel - Variables & Debugging

### **Variables Section:**
For each variable discovered during execution:

```
🔹 current_applicant (Section Variable)
   ID: SEC_0f962e4d-a932-4958-9352-b54e0ef92be5
   Cypher: MATCH (a:Applicant {applicantId:$applicantId}) RETURN a
   Status: ✅ Resolved
   Value: { "applicantId": "...", "type": "PRIMARY" }

🔸 is_coapplicant_flow (Section Variable)  
   ID: SEC_0f962e4d-a932-4958-9352-b54e0ef92be5
   Cypher: RETURN $isCoApplicant = 'true'
   Status: ✅ Resolved  
   Value: false

🔸 dealer_address_exists (Section Variable)
   ID: SEC_1a879403-51e3-4eef-b6c5-00a613f8f76e
   Cypher: MATCH (src)-[:SUPPLIES]->(d:Datapoint)...
   Status: ⏳ Waiting for data
   Reason: Question Q_AD_Residential_Address_(Customer-Current) not answered

❌ new_coapplicant (Action Variable)
   ID: action_1750257012185_5g88fb  
   Cypher: MATCH (ca:Applicant) WHERE id(ca) = {{ createdNodeIds[0] }} RETURN ca
   Status: ❌ Error
   Error: Variable 'createdNodeIds' not available
```

### **askWhen Evaluation Section:**
```
🔍 Edge Conditions
┌─ Living Situation → Q_AD_Address_Check
│  askWhen: python: {{ dealer_address_exists }} == True
│  Status: ⏳ Waiting (dealer_address_exists pending)
│  
└─ Living Situation → Q_AD_Residential_Address_(Customer-Current)  
   askWhen: python: {{ dealer_address_exists }} == False
   Status: ✅ Will execute when reached
```

### **Source Node Resolution:**
```
🎯 Source Node Tracking
Current: { "applicantId": "...", "type": "PRIMARY" }
History:
├─ Get a Quote: {{ current_applicant }} → Applicant:123
└─ Action Chain: {{ primary_applicant }} → Applicant:123
```

## Bottom Panel - Execution Controls

### **JSON Editor (Left Side):**
```json
{
  "sectionId": "SEC_0f962e4d-a932-4958-9352-b54e0ef92be5",
  "applicationId": "app_123",
  "applicantId": "applicant_456",
  "isPrimaryFlow": true
}
```

**Features:**
- **Syntax highlighting** with validation
- **Auto-complete** for known sectionIds/parameters
- **Save to browser**: Current payload persisted
- **Template shortcuts**: Common payload patterns

### **Execution Controls (Center):**
```
🚀 [RUN FLOW]  ⏸️ [STEP THROUGH]  🔄 [RESET]  📋 [COPY RESPONSE]
```

### **History & Favorites (Right Side):**
```
📚 Run History                   ⭐ Favorites
├─ Get a Quote - Primary (2m ago)    ├─ 🌟 Happy Path Test
├─ Living Situation (5m ago)         └─ 🌟 Error Scenario  
└─ Address Flow Error (1h ago)      
```

**Features:**
- **Named runs**: Give meaningful names to test scenarios
- **Quick replay**: One-click to rerun previous executions
- **Comparison**: Diff between runs
- **Export/Import**: Share test scenarios with team

## Technical Implementation

### **Backend (FastAPI + SQLite):**

1. **New Debugging Endpoints:**
   - `GET /debug/tracks` - List all tracks with sections
   - `POST /debug/execute` - Enhanced execution with detailed tracing
   - `GET /debug/history` - Execution history
   - `POST /debug/favorites` - Save/load favorite runs

2. **Enhanced Response Format:**
```json
{
  "execution": {
    "sectionId": "...",
    "question": {...},
    "completed": false,
    // ... existing fields
  },
  "debugInfo": {
    "traversalPath": [
      {
        "nodeType": "Section",
        "nodeId": "SEC_...",
        "action": "evaluated",
        "timestamp": "...",
        "duration": 12
      }
    ],
    "variableEvaluations": [
      {
        "name": "current_applicant", 
        "source": "section",
        "expression": "MATCH...",
        "status": "resolved",
        "value": {...},
        "duration": 45
      }
    ],
    "conditionEvaluations": [
      {
        "edge": "SEC_...->Q_...",
        "askWhen": "python: ...",
        "result": true,
        "variables": ["dealer_address_exists"]
      }
    ]
  }
}
```

3. **SQLite Schema:**
```sql
CREATE TABLE execution_history (
  id INTEGER PRIMARY KEY,
  name TEXT,
  payload TEXT, -- JSON
  response TEXT, -- JSON  
  created_at TIMESTAMP,
  duration_ms INTEGER,
  is_favorite BOOLEAN
);
```

### **Frontend (React + D3.js):**

1. **Components:**
   - `TrackBrowser` - Left panel navigation
   - `FlowCanvas` - Main D3.js visualization  
   - `DebugPanel` - Right panel variables/conditions
   - `ExecutionControls` - Bottom panel editor/controls

2. **State Management:**
   - **Redux/Zustand** for global execution state
   - **Local Storage** for UI preferences and history
   - **WebSocket** connection for real-time execution updates

3. **Visualization Library:**
   - **D3.js + React** for flow graph rendering
   - **Force-directed layout** for automatic node positioning
   - **Custom shapes** for different node types
   - **Animation** for execution flow

### **Port 5667 Deployment:**
```bash
# Development server
npm run dev -- --port 5667

# Production build  
npm run build
serve -p 5667 build/
```

## Key Benefits

1. **Complete Flow Visibility**: See exactly how the engine traverses your graph
2. **Variable Debugging**: Track complex variable resolution and dependencies  
3. **Condition Analysis**: Understand why certain paths are taken or skipped
4. **Performance Insights**: Identify slow variable evaluations or Cypher queries
5. **Test Automation**: Save and replay common test scenarios
6. **Team Collaboration**: Share debugging sessions and test cases

This interface will make debugging your complex flow engine much more intuitive and efficient, especially for understanding the intricate variable dependencies and conditional logic in your flows.

Would you like me to proceed with implementing this design?
