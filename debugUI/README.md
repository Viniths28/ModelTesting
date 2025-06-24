# Flow Engine Debug UI - Enhanced Edition

A comprehensive debugging interface for the Flow Engine with support for all recent enhancements including variable placeholder syntax, enhanced source node resolution, and comprehensive debug capture.

## 🚀 Enhanced Features

### Recent Engine Enhancements Supported
- **Variable Placeholder Support**: Full support for `{{ variable }}` template syntax
- **Enhanced Source Node Resolution**: Support for variable placeholders in sourceNode expressions
- **Template Substitution**: Double-mustache syntax with JSON literal replacement
- **isPrimaryFlow Parameter**: Complete support for primary/secondary flow execution modes
- **Lazy Variable Loading**: Variables are resolved on-demand with intelligent caching
- **Security Sandbox**: Enhanced Python evaluation with timeout protection

### Debug UI Features
- **Multi-Panel Interface**: Left (Track Browser), Main (Flow Canvas), Right (Debug Info), Bottom (Execution Controls)
- **Real-time Flow Visualization**: Interactive step-by-step execution with D3.js
- **Comprehensive Debug Capture**: Variables, conditions, source nodes, traversal paths, timing
- **Execution History**: Persistent storage with favorites and custom naming
- **JSON Payload Editor**: Monaco editor with validation and auto-population
- **Connection Monitoring**: Real-time backend health checking

## 🏗️ Architecture

### Backend (FastAPI + SQLite + Neo4j)
```
debugUI/backend/
├── app.py              # Main FastAPI application with enhanced API endpoints
├── models.py           # Pydantic models with isPrimaryFlow support
├── database.py         # SQLite database manager for execution history
├── debug_engine.py     # Enhanced flow engine with debug capture
└── requirements.txt    # Python dependencies
```

### Frontend (React + Tailwind + D3.js)
```
debugUI/frontend/
├── src/
│   ├── App.js                      # Main application with layout management
│   ├── store/debugStore.js         # Zustand state management with persistence
│   ├── utils/api.js                # API utilities with error handling
│   ├── components/
│   │   ├── TrackBrowser.js         # Left panel - hierarchical track navigation
│   │   ├── FlowCanvas.js           # Main panel - flow visualization
│   │   ├── DebugPanel.js           # Right panel - debug information tabs
│   │   └── ExecutionControls.js    # Bottom panel - JSON editor & controls
│   └── index.css                   # Tailwind CSS with custom debug styles
├── package.json                    # React dependencies
├── tailwind.config.js              # Tailwind configuration
└── postcss.config.js               # PostCSS configuration
```

## 🛠️ Quick Start

### Prerequisites
- **Python 3.8+** (for backend)
- **Node.js 16+** (for frontend)
- **Neo4j** running on `bolt://localhost:7689` with credentials `neo4j/testpassword`

### One-Click Setup & Launch
```bash
# Navigate to the debugUI directory
cd debugUI

# Run the setup script (handles everything automatically)
python start.py
```

The script will:
1. ✅ Check prerequisites (Python, Node.js, Neo4j)
2. 📦 Set up Python virtual environment and install dependencies
3. 📦 Install npm dependencies
4. 🚀 Launch backend server on port 8001
5. 🚀 Launch frontend server on port 3000
6. 🎉 Open your browser to http://localhost:3000

### Manual Setup (Alternative)

#### Backend Setup
```bash
cd debugUI/backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

#### Frontend Setup
```bash
cd debugUI/frontend
npm install
npm start
```

## 📊 API Endpoints

### Enhanced Debug Execution
```http
POST /api/execute
Content-Type: application/json

{
  "sectionId": "SEC_APPLICANT_DETAILS",
  "applicationId": "app_12345",
  "applicantId": "applicant_67890",
  "isPrimaryFlow": true
}
```

### Track Management
- `GET /api/tracks` - Get available tracks
- `POST /api/tracks/access` - Record track access
- `GET /api/tracks/recent` - Get recently accessed tracks

### Execution History
- `GET /api/history` - Get execution history
- `GET /api/favorites` - Get favorite executions
- `POST /api/favorites/toggle` - Toggle favorite status
- `POST /api/executions/update-name` - Update execution name

### System
- `GET /api/health` - Health check with Neo4j status
- `GET /api/sections/{sectionId}` - Get section details

## 🎯 Usage Guide

### 1. Track Navigation
- Use the **Track Browser** (left panel) to explore available tracks
- Click on tracks to expand and view sections
- Select a section to auto-populate the JSON payload

### 2. Execution with Enhanced Features
- **JSON Payload Editor**: Edit execution parameters in the bottom panel
- **isPrimaryFlow Parameter**: Set to `true` for primary flow, `false` for secondary
- **Template Variables**: Use `{{ variable }}` syntax in your flow definitions
- **Execute**: Click "Execute Flow" to run with comprehensive debug capture

### 3. Debug Information
- **Variables Tab**: View all variable evaluations with status, values, and timing
- **Conditions Tab**: See condition evaluations with results and variables used
- **Source Nodes Tab**: Inspect source node resolutions and expressions
- **Traversal Path**: Step through execution with detailed timing information

### 4. History & Favorites
- **Execution History**: All executions are automatically saved
- **Favorites**: Mark important executions for quick access
- **Custom Names**: Rename executions for better organization
- **Persistence**: UI state and preferences are saved in browser storage

## 🔧 Enhanced Engine Features

### Variable Placeholder Support
The engine now supports `{{ variable }}` syntax for template substitution:

```cypher
// In Neo4j node properties
MATCH (app:Application {applicationId: '{{ applicationId }}'})
RETURN app
```

### Enhanced Source Node Resolution
Source nodes can now use variable placeholders:

```json
{
  "sourceNode": "{{ current_applicant }}",
  "askWhen": "{{ applicant_age }} > 18"
}
```

### Template Substitution
Double-mustache placeholders are replaced with JSON literals:

```python
# Python evaluator with template
age = {{ applicant.age }}
return age >= 21
```

## 🚨 Troubleshooting

### Backend Issues
- **Neo4j Connection Failed**: Ensure Neo4j is running on `bolt://localhost:7689`
- **Import Errors**: Check that the flow_engine_project is in the correct relative path
- **Port 8001 in Use**: Change the port in `app.py` and update frontend proxy

### Frontend Issues
- **API Connection Failed**: Verify backend is running on port 8001
- **Build Errors**: Delete `node_modules` and run `npm install` again
- **Browser Compatibility**: Use Chrome/Firefox/Safari for best experience

### Debug Capture Issues
- **Missing Debug Info**: Ensure you're using the enhanced debug endpoints
- **Variable Resolution Errors**: Check template syntax and variable definitions
- **Timeout Issues**: Adjust timeout values in evaluator configuration

## 🔄 Data Flow

1. **User Input**: JSON payload with `isPrimaryFlow` parameter
2. **Backend Processing**: Enhanced debug engine captures comprehensive information
3. **Database Storage**: Execution history stored in SQLite with full debug context
4. **Frontend Visualization**: Real-time display of execution steps and debug data
5. **Persistence**: UI state and favorites saved to browser storage

## 🎨 UI Components

### Track Browser (Left Panel)
- Hierarchical tree view of tracks and sections
- Auto-expansion and section variable preview
- Recent tracks and access analytics
- Browser storage persistence

### Flow Canvas (Main Panel)
- D3.js-powered flow visualization
- Interactive node selection with step-by-step execution
- Real-time progress indicators
- Different node types (Section/Question/Action)

### Debug Panel (Right Panel)
- Tabbed interface for Variables, Conditions, Source Nodes
- Real-time debug information display
- Execution timing and performance metrics
- Error and warning indicators

### Execution Controls (Bottom Panel)
- Monaco editor for JSON payload editing
- Execution history browser with search and filtering
- Favorites management with custom naming
- Connection status and health monitoring

## 📈 Performance Features

- **Lazy Loading**: Components and data loaded on demand
- **Caching**: Intelligent caching of API responses and UI state
- **Debouncing**: Input debouncing for smooth user experience
- **Virtualization**: Efficient rendering of large lists
- **Error Boundaries**: Graceful error handling and recovery

## 🔐 Security Features

- **CORS Configuration**: Proper cross-origin resource sharing setup
- **Input Validation**: Comprehensive request validation with Pydantic
- **Timeout Protection**: Execution timeouts to prevent hanging
- **Error Sanitization**: Safe error message handling
- **Secure Evaluation**: Sandboxed Python execution environment

## 📝 Development

### Adding New Features
1. **Backend**: Add new endpoints in `app.py`, models in `models.py`
2. **Frontend**: Create new components in `src/components/`
3. **State Management**: Extend `debugStore.js` for new state requirements
4. **Styling**: Add custom styles in `index.css` with Tailwind classes

### Testing
- **Backend**: Use FastAPI's automatic documentation at `/docs`
- **Frontend**: Use React Developer Tools for component inspection
- **API**: Test endpoints with Postman or curl
- **Database**: Inspect SQLite database with DB Browser

## 🚀 Production Deployment

### Backend
```bash
# Install production dependencies
pip install gunicorn

# Run with Gunicorn
gunicorn app:app --host 0.0.0.0 --port 5667 --workers 4
```

### Frontend
```bash
# Build for production
npm run build

# Serve with nginx or Apache
# Configure reverse proxy to backend
```

### Environment Variables
```bash
# Backend
export NEO4J_URI=bolt://localhost:7689
export NEO4J_USER=neo4j
export NEO4J_PASSWORD=testpassword
export DATABASE_URL=sqlite:///debug_ui.db

# Frontend
export REACT_APP_API_URL=http://localhost:8001
```

## 📚 Additional Resources

- **Flow Engine Documentation**: See `flow_engine_project/` for core engine docs
- **Neo4j Documentation**: https://neo4j.com/docs/
- **FastAPI Documentation**: https://fastapi.tiangolo.com/
- **React Documentation**: https://reactjs.org/docs/
- **Tailwind CSS**: https://tailwindcss.com/docs

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 📝 Testing Notes

### First Phase Testing
- **Multiple Applicant Scenarios**: Testing flow execution with various applicant configurations
- **Bug Tracking**: Identifying and documenting issues in multi-applicant flows
- **Performance Analysis**: Monitoring execution times and resource usage
- **Edge Case Handling**: Testing boundary conditions and error scenarios

Known issues in first phase:
- Multiple applicant variable resolution needs refinement
- Complex conditional logic evaluation requires optimization
- Performance bottlenecks in large flow visualizations

---

**Built with ❤️ for comprehensive Flow Engine debugging** 