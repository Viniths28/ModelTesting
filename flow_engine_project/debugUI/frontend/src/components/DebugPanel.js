import React, { useState } from 'react';
import { useDebugStore } from '../store/debugStore';
import { 
  CheckCircle, 
  XCircle, 
  Clock, 
  AlertCircle, 
  ChevronRight, 
  ChevronDown,
  Database,
  Code,
  Target
} from 'lucide-react';

const DebugPanel = () => {
  const { debugInfo, selectedNode, executionResult } = useDebugStore();
  const [activeTab, setActiveTab] = useState('variables');
  const [expandedItems, setExpandedItems] = useState(new Set());

  const toggleExpanded = (id) => {
    setExpandedItems(prev => {
      const newSet = new Set(prev);
      if (newSet.has(id)) {
        newSet.delete(id);
      } else {
        newSet.add(id);
      }
      return newSet;
    });
  };

  const renderVariableStatus = (variable) => {
    switch (variable.status) {
      case 'RESOLVED':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'ERROR':
        return <XCircle className="w-4 h-4 text-red-600" />;
      case 'WAITING':
        return <Clock className="w-4 h-4 text-yellow-600" />;
      default:
        return <AlertCircle className="w-4 h-4 text-gray-400" />;
    }
  };

  const renderVariableValue = (value) => {
    if (value === null || value === undefined) {
      return <span className="text-gray-400 italic">null</span>;
    }
    
    if (typeof value === 'object') {
      return (
        <pre className="text-xs bg-gray-100 p-2 rounded max-h-32 overflow-y-auto">
          {JSON.stringify(value, null, 2)}
        </pre>
      );
    }
    
    return <span className="text-sm">{String(value)}</span>;
  };

  const tabs = [
    { id: 'variables', label: 'Variables', icon: Database },
    { id: 'conditions', label: 'Conditions', icon: Code },
    { id: 'sources', label: 'Source Nodes', icon: Target }
  ];

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900">Debug Information</h2>
        
        {/* Tabs */}
        <div className="flex mt-3 space-x-1">
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

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {!debugInfo ? (
          <div className="p-4 text-center text-gray-500">
            <AlertCircle className="w-8 h-8 mx-auto mb-2 text-gray-400" />
            <p className="text-sm">No debug information available</p>
            <p className="text-xs text-gray-400 mt-1">
              Run a flow execution to see debug details
            </p>
          </div>
        ) : (
          <>
            {/* Variables Tab */}
            {activeTab === 'variables' && (
              <div className="p-4">
                <div className="space-y-3">
                  {debugInfo.variableEvaluations?.length > 0 ? (
                    debugInfo.variableEvaluations.map((variable, index) => (
                      <div
                        key={index}
                        className={`variable-item rounded-lg border p-3 ${
                          variable.status === 'RESOLVED' ? 'bg-green-50 border-green-200' :
                          variable.status === 'ERROR' ? 'bg-red-50 border-red-200' :
                          'bg-yellow-50 border-yellow-200'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center space-x-2">
                            {renderVariableStatus(variable)}
                            <div>
                              <h4 className="font-medium text-sm">{variable.name}</h4>
                              <p className="text-xs text-gray-500">
                                {variable.source} • {variable.sourceId}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => toggleExpanded(`var-${index}`)}
                            className="p-1 hover:bg-gray-200 rounded"
                          >
                            {expandedItems.has(`var-${index}`) ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : (
                              <ChevronRight className="w-4 h-4" />
                            )}
                          </button>
                        </div>

                        {expandedItems.has(`var-${index}`) && (
                          <div className="mt-3 space-y-2">
                            <div>
                              <p className="text-xs font-medium text-gray-700">Expression:</p>
                              <code className="text-xs bg-gray-100 p-1 rounded block">
                                {variable.expression}
                              </code>
                            </div>
                            
                            {variable.status === 'RESOLVED' && (
                              <div>
                                <p className="text-xs font-medium text-gray-700">Value:</p>
                                {renderVariableValue(variable.value)}
                              </div>
                            )}
                            
                            {variable.error && (
                              <div>
                                <p className="text-xs font-medium text-red-700">Error:</p>
                                <p className="text-xs text-red-600">{variable.error}</p>
                              </div>
                            )}
                            
                            <div className="flex justify-between text-xs text-gray-500">
                              <span>Duration: {variable.duration}ms</span>
                              {variable.dependencies?.length > 0 && (
                                <span>Dependencies: {variable.dependencies.join(', ')}</span>
                              )}
                            </div>
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500 text-center">
                      No variable evaluations recorded
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Conditions Tab */}
            {activeTab === 'conditions' && (
              <div className="p-4">
                <div className="space-y-3">
                  {debugInfo.conditionEvaluations?.length > 0 ? (
                    debugInfo.conditionEvaluations.map((condition, index) => (
                      <div
                        key={index}
                        className={`border rounded-lg p-3 ${
                          condition.result 
                            ? 'bg-green-50 border-green-200' 
                            : 'bg-red-50 border-red-200'
                        }`}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center space-x-2">
                            {condition.result ? (
                              <CheckCircle className="w-4 h-4 text-green-600" />
                            ) : (
                              <XCircle className="w-4 h-4 text-red-600" />
                            )}
                            <div>
                              <h4 className="font-medium text-sm">
                                {condition.sourceNode} → {condition.targetNode}
                              </h4>
                              <p className="text-xs text-gray-500">
                                Result: {condition.result ? 'TRUE' : 'FALSE'}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => toggleExpanded(`cond-${index}`)}
                            className="p-1 hover:bg-gray-200 rounded"
                          >
                            {expandedItems.has(`cond-${index}`) ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : (
                              <ChevronRight className="w-4 h-4" />
                            )}
                          </button>
                        </div>

                        {expandedItems.has(`cond-${index}`) && (
                          <div className="mt-3 space-y-2">
                            <div>
                              <p className="text-xs font-medium text-gray-700">askWhen:</p>
                              <code className="text-xs bg-gray-100 p-1 rounded block">
                                {condition.askWhen}
                              </code>
                            </div>
                            
                            {condition.variables?.length > 0 && (
                              <div>
                                <p className="text-xs font-medium text-gray-700">Variables Used:</p>
                                <p className="text-xs text-gray-600">
                                  {condition.variables.join(', ')}
                                </p>
                              </div>
                            )}
                            
                            {condition.error && (
                              <div>
                                <p className="text-xs font-medium text-red-700">Error:</p>
                                <p className="text-xs text-red-600">{condition.error}</p>
                              </div>
                            )}
                            
                            <p className="text-xs text-gray-500">
                              Duration: {condition.duration}ms
                            </p>
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500 text-center">
                      No condition evaluations recorded
                    </p>
                  )}
                </div>
              </div>
            )}

            {/* Source Nodes Tab */}
            {activeTab === 'sources' && (
              <div className="p-4">
                <div className="space-y-3">
                  {debugInfo.sourceNodeHistory?.length > 0 ? (
                    debugInfo.sourceNodeHistory.map((source, index) => (
                      <div
                        key={index}
                        className="border rounded-lg p-3 bg-gray-50"
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex items-center space-x-2">
                            <Target className="w-4 h-4 text-blue-600" />
                            <div>
                              <h4 className="font-medium text-sm">
                                {source.nodeId || 'Unknown Node'}
                              </h4>
                              <p className="text-xs text-gray-500">
                                Status: {source.status}
                              </p>
                            </div>
                          </div>
                          <button
                            onClick={() => toggleExpanded(`source-${index}`)}
                            className="p-1 hover:bg-gray-200 rounded"
                          >
                            {expandedItems.has(`source-${index}`) ? (
                              <ChevronDown className="w-4 h-4" />
                            ) : (
                              <ChevronRight className="w-4 h-4" />
                            )}
                          </button>
                        </div>

                        {expandedItems.has(`source-${index}`) && (
                          <div className="mt-3 space-y-2">
                            {source.expression && (
                              <div>
                                <p className="text-xs font-medium text-gray-700">Expression:</p>
                                <code className="text-xs bg-gray-100 p-1 rounded block">
                                  {source.expression}
                                </code>
                              </div>
                            )}
                            
                            {source.value && (
                              <div>
                                <p className="text-xs font-medium text-gray-700">Value:</p>
                                {renderVariableValue(source.value)}
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-gray-500 text-center">
                      No source node history recorded
                    </p>
                  )}
                </div>
              </div>
            )}
          </>
        )}
      </div>

      {/* Selected Node Details */}
      {selectedNode && (
        <div className="border-t border-gray-200 p-4 bg-gray-50">
          <h3 className="font-medium text-sm mb-2">Selected Node</h3>
          <div className="space-y-2">
            <div>
              <span className="text-xs font-medium text-gray-700">Type:</span>
              <span className="text-xs ml-2 capitalize">{selectedNode.type}</span>
            </div>
            <div>
              <span className="text-xs font-medium text-gray-700">ID:</span>
              <span className="text-xs ml-2">{selectedNode.id}</span>
            </div>
            <div>
              <span className="text-xs font-medium text-gray-700">Name:</span>
              <span className="text-xs ml-2">{selectedNode.name}</span>
            </div>
            {selectedNode.step && (
              <div>
                <span className="text-xs font-medium text-gray-700">Step:</span>
                <span className="text-xs ml-2">{selectedNode.step}</span>
              </div>
            )}
            {selectedNode.duration && (
              <div>
                <span className="text-xs font-medium text-gray-700">Duration:</span>
                <span className="text-xs ml-2">{selectedNode.duration}ms</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default DebugPanel; 