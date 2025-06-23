import React, { useState, useEffect } from 'react';
import { Wifi, WifiOff } from 'lucide-react';
import TrackBrowser from './components/TrackBrowser';
import FlowCanvas from './components/FlowCanvas';
import DebugPanel from './components/DebugPanel';
import ExecutionControls from './components/ExecutionControls';
import { useDebugStore } from './store/debugStore';
import api from './utils/api';

function App() {
  const [isConnected, setIsConnected] = useState(false);
  const { selectedTrack, selectedSection, executionResult, debugInfo } = useDebugStore();

  // Health check to verify backend connection
  useEffect(() => {
    const checkConnection = async () => {
      try {
        await api.get('/health');
        setIsConnected(true);
      } catch (error) {
        setIsConnected(false);
      }
    };

    checkConnection();
    const interval = setInterval(checkConnection, 30000); // Check every 30 seconds
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen flex flex-col bg-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-3 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <h1 className="text-xl font-semibold text-gray-900">
            Flow Engine Debug Interface
          </h1>
          {selectedSection && (
            <span className="text-sm text-gray-500">
              {selectedTrack?.trackName} → {selectedSection.sectionName}
            </span>
          )}
        </div>
        
        <div className="flex items-center space-x-2">
          {isConnected ? (
            <div className="flex items-center text-green-600">
              <Wifi className="w-4 h-4 mr-1" />
              <span className="text-sm">Connected</span>
            </div>
          ) : (
            <div className="flex items-center text-red-600">
              <WifiOff className="w-4 h-4 mr-1" />
              <span className="text-sm">Disconnected</span>
            </div>
          )}
        </div>
      </header>

      {/* Main Layout - 3 panel layout as specified */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Track Browser (300px) */}
        <div className="w-80 bg-white border-r border-gray-200 flex flex-col">
          <TrackBrowser />
        </div>

        {/* Main Canvas - Flow Visualization (flex) */}
        <div className="flex-1 bg-gray-50 flex flex-col">
          <FlowCanvas />
        </div>

        {/* Right Panel - Variables & Debugging (350px) */}
        <div className="w-96 bg-white border-l border-gray-200 flex flex-col">
          <DebugPanel />
        </div>
      </div>

      {/* Bottom Panel - JSON Editor & Execution Controls (300px) */}
      <div className="h-80 bg-white border-t border-gray-200">
        <ExecutionControls />
      </div>
    </div>
  );
}

export default App; 