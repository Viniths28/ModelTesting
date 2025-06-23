import React, { useState, useEffect } from 'react';
import { useDebugStore } from '../store/debugStore';
import { apiHelpers } from '../utils/api';
import { 
  Play, 
  RotateCcw, 
  Copy, 
  History, 
  Star, 
  Clock,
  Edit3,
  Trash2,
  Download,
  Upload
} from 'lucide-react';

const ExecutionControls = () => {
  const {
    currentPayload,
    setCurrentPayload,
    updatePayloadField,
    selectedSection,
    isExecuting,
    setIsExecuting,
    setExecutionResult,
    executionHistory,
    favorites,
    clearExecution,
    addToFavorites,
    replayExecution,
    addExecutionHistoryItem
  } = useDebugStore();

  // Keep a local editable JSON string so users can type even while the JSON is temporarily invalid
  const [payloadText, setPayloadText] = useState(() => JSON.stringify(currentPayload, null, 2));
  const [activeTab, setActiveTab] = useState('editor');
  const [executionName, setExecutionName] = useState('');
  const [jsonError, setJsonError] = useState('');
  const [editingHistory, setEditingHistory] = useState(null);

  useEffect(() => {
    // Generate default execution name
    if (selectedSection) {
      setExecutionName(`${selectedSection.sectionName} - ${new Date().toLocaleTimeString()}`);
    }

    // Sync local text when currentPayload changes externally (e.g., replay)
    setPayloadText(JSON.stringify(currentPayload, null, 2));
  }, [selectedSection, currentPayload]);

  const handlePayloadChange = (value) => {
    setPayloadText(value);
    try {
      const parsed = JSON.parse(value);
      setCurrentPayload(parsed);
      setJsonError('');
    } catch (error) {
      setJsonError(error.message);
    }
  };

  const handleExecute = async () => {
    if (!selectedSection) {
      alert('Please select a section first');
      return;
    }

    if (jsonError) {
      alert('Please fix JSON errors before executing');
      return;
    }

    setIsExecuting(true);
    try {
      const response = await apiHelpers.executeFlow(currentPayload, executionName);
      setExecutionResult(response.execution, response.debugInfo);
    } catch (error) {
      console.error('Execution failed:', error);
      alert(`Execution failed: ${error.message || 'Unknown error'}`);

      // Record failure in history list
      addExecutionHistoryItem({
        id: Date.now(),
        timestamp: new Date().toISOString(),
        sectionId: selectedSection?.sectionId || 'unknown',
        payload: currentPayload,
        name: executionName || 'Untitled Execution',
        error: error?.response?.data || error.message || 'Unknown error',
        status: 'failed'
      });
    } finally {
      setIsExecuting(false);
    }
  };

  const handleReset = () => {
    clearExecution();
  };

  const handleCopyResponse = () => {
    // This would copy the last execution result
    // Implementation depends on what you want to copy
    navigator.clipboard.writeText(JSON.stringify(currentPayload, null, 2));
  };

  const handleReplayExecution = (execution) => {
    replayExecution(execution);
    setExecutionName(`${execution.name} (Replay)`);
  };

  const handleAddToFavorites = (execution) => {
    addToFavorites(execution);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
  };

  const tabs = [
    { id: 'editor', label: 'JSON Editor', icon: Edit3 },
    { id: 'history', label: 'History', icon: History },
    { id: 'favorites', label: 'Favorites', icon: Star }
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b border-gray-200">
        <div className="flex items-center space-x-4">
          {/* Tabs */}
          <div className="flex space-x-1">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                onClick={() => setActiveTab(id)}
                className={`flex items-center px-3 py-2 text-sm rounded ${
                  activeTab === id
                    ? 'bg-blue-100 text-blue-700 border border-blue-200'
                    : 'text-gray-600 hover:text-gray-800 hover:bg-gray-100'
                }`}
              >
                <Icon className="w-4 h-4 mr-2" />
                {label}
              </button>
            ))}
          </div>
        </div>

        {/* Execution Controls */}
        <div className="flex items-center space-x-2">
          <input
            type="text"
            placeholder="Execution name..."
            value={executionName}
            onChange={(e) => setExecutionName(e.target.value)}
            className="px-3 py-2 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          
          <button
            onClick={handleExecute}
            disabled={isExecuting || !selectedSection}
            className="flex items-center px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className="w-4 h-4 mr-2" />
            {isExecuting ? 'Running...' : 'Run Flow'}
          </button>
          
          <button
            onClick={handleReset}
            className="flex items-center px-3 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
          >
            <RotateCcw className="w-4 h-4 mr-2" />
            Reset
          </button>
          
          <button
            onClick={handleCopyResponse}
            className="flex items-center px-3 py-2 text-gray-600 border border-gray-300 rounded hover:bg-gray-50"
          >
            <Copy className="w-4 h-4 mr-2" />
            Copy
          </button>
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        {/* JSON Editor Tab */}
        {activeTab === 'editor' && (
          <div className="h-full flex">
            <div className="flex-1 p-4">
              <div className="h-full flex flex-col">
                <div className="flex items-center justify-between mb-2">
                  <h3 className="text-sm font-medium text-gray-700">Request Payload</h3>
                  {jsonError && (
                    <span className="text-xs text-red-600">Error: {jsonError}</span>
                  )}
                </div>
                
                <textarea
                  value={payloadText}
                  onChange={(e) => handlePayloadChange(e.target.value)}
                  className={`flex-1 w-full p-3 text-sm font-mono border rounded-md resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                    jsonError ? 'border-red-300' : 'border-gray-300'
                  }`}
                  placeholder="Enter JSON payload..."
                />
                
                <div className="mt-2 flex space-x-2">
                  <button
                    onClick={() => updatePayloadField('sectionId', selectedSection?.sectionId || '')}
                    disabled={!selectedSection}
                    className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200 disabled:opacity-50"
                  >
                    Use Selected Section
                  </button>
                  <button
                    onClick={() => setCurrentPayload({
                      sectionId: selectedSection?.sectionId || '',
                      applicationId: 'app_123',
                      applicantId: 'applicant_456',
                      isPrimaryFlow: true
                    })}
                    className="px-3 py-1 text-xs bg-gray-100 text-gray-700 rounded hover:bg-gray-200"
                  >
                    Reset to Default
                  </button>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* History Tab */}
        {activeTab === 'history' && (
          <div className="h-full overflow-y-auto p-4">
            <div className="space-y-2">
              {executionHistory.length > 0 ? (
                executionHistory.map((execution) => (
                  <div
                    key={execution.id}
                    className="border rounded-lg p-3 hover:bg-gray-50"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <h4 className="font-medium text-sm">{execution.name}</h4>
                          {execution.status === 'failed' || execution.error ? (
                            <span className="px-2 py-1 text-xs rounded bg-red-100 text-red-800">Failed</span>
                          ) : (
                            <span className={`px-2 py-1 text-xs rounded ${
                              execution.result?.completed 
                                ? 'bg-green-100 text-green-800' 
                                : 'bg-blue-100 text-blue-800'
                            }`}>
                              {execution.result?.completed ? 'Completed' : 'Stopped'}
                            </span>
                          )}
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          <Clock className="w-3 h-3 inline mr-1" />
                          {formatDate(execution.timestamp)}
                        </p>
                        <p className="text-xs text-gray-500">
                          Section: {execution.sectionId}
                        </p>
                      </div>
                      
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => handleReplayExecution(execution)}
                          className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded"
                          title="Replay"
                        >
                          <Play className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => handleAddToFavorites(execution)}
                          className="p-2 text-gray-600 hover:text-yellow-600 hover:bg-yellow-50 rounded"
                          title="Add to Favorites"
                        >
                          <Star className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setEditingHistory(execution.id)}
                          className="p-2 text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded"
                          title="Edit Name"
                        >
                          <Edit3 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                    
                    {execution.debugInfo && (
                      <div className="mt-2 flex space-x-4 text-xs text-gray-500">
                        <span>Steps: {execution.debugInfo.traversalPath?.length || 0}</span>
                        <span>Variables: {execution.debugInfo.variableEvaluations?.length || 0}</span>
                        <span>Duration: {execution.debugInfo.totalDuration || 0}ms</span>
                      </div>
                    )}

                    {execution.error && (
                      <details className="mt-2 text-xs text-red-700">
                        <summary className="cursor-pointer">Error details</summary>
                        <pre className="whitespace-pre-wrap break-all bg-red-50 p-2 rounded">
                          {typeof execution.error === 'string' ? execution.error : JSON.stringify(execution.error, null, 2)}
                        </pre>
                      </details>
                    )}
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 py-8">
                  <History className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                  <p className="text-sm">No execution history</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Run a flow execution to see history
                  </p>
                </div>
              )}
            </div>
          </div>
        )}

        {/* Favorites Tab */}
        {activeTab === 'favorites' && (
          <div className="h-full overflow-y-auto p-4">
            <div className="space-y-2">
              {favorites.length > 0 ? (
                favorites.map((favorite) => (
                  <div
                    key={favorite.id}
                    className="border rounded-lg p-3 hover:bg-gray-50 bg-yellow-50 border-yellow-200"
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <Star className="w-4 h-4 text-yellow-600" />
                          <h4 className="font-medium text-sm">{favorite.name}</h4>
                        </div>
                        <p className="text-xs text-gray-500 mt-1">
                          Added: {formatDate(favorite.addedAt)}
                        </p>
                        <p className="text-xs text-gray-500">
                          Section: {favorite.sectionId}
                        </p>
                      </div>
                      
                      <div className="flex items-center space-x-1">
                        <button
                          onClick={() => handleReplayExecution(favorite)}
                          className="p-2 text-gray-600 hover:text-blue-600 hover:bg-blue-50 rounded"
                          title="Replay"
                        >
                          <Play className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => {/* Remove from favorites */}}
                          className="p-2 text-gray-600 hover:text-red-600 hover:bg-red-50 rounded"
                          title="Remove from Favorites"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center text-gray-500 py-8">
                  <Star className="w-8 h-8 mx-auto mb-2 text-gray-400" />
                  <p className="text-sm">No favorites saved</p>
                  <p className="text-xs text-gray-400 mt-1">
                    Add executions to favorites from history
                  </p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default ExecutionControls; 