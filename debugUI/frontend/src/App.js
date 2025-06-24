import React, { useEffect, useState } from 'react';
import { AlertCircle, CheckCircle, Loader, Wifi, WifiOff } from 'lucide-react';
import useDebugStore from './store/debugStore';
import { testConnection, debugApi } from './utils/api';

// Import components (we'll create these next)
import TrackBrowser from './components/TrackBrowser';
import FlowCanvas from './components/FlowCanvas';
import DebugPanel from './components/DebugPanel';
import ExecutionControls from './components/ExecutionControls';

function App() {
  const {
    connectionStatus,
    setConnectionStatus,
    setTracks,
    leftPanelWidth,
    rightPanelWidth,
    bottomPanelHeight,
    showBottomPanel
  } = useDebugStore();

  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize connection and load data
  useEffect(() => {
    const initialize = async () => {
      setIsLoading(true);
      setError(null);

      try {
        // Test backend connection
        const connectionResult = await testConnection();
        
        if (connectionResult.success) {
          setConnectionStatus('connected');
          
          // Load initial data
          try {
            const tracks = await debugApi.getTracks();
            setTracks(tracks);
          } catch (trackError) {
            console.warn('Failed to load tracks:', trackError);
            // Don't fail completely if tracks can't be loaded
          }
        } else {
          setConnectionStatus('error');
          setError(connectionResult.message);
        }
      } catch (err) {
        setConnectionStatus('error');
        setError('Failed to initialize application');
        console.error('Initialization error:', err);
      } finally {
        setIsLoading(false);
      }
    };

    initialize();

    // Set up periodic health check
    const healthCheckInterval = setInterval(async () => {
      try {
        await debugApi.healthCheck();
        if (connectionStatus !== 'connected') {
          setConnectionStatus('connected');
          setError(null);
        }
      } catch (err) {
        if (connectionStatus !== 'error') {
          setConnectionStatus('error');
          setError('Connection lost to backend');
        }
      }
    }, 30000); // Check every 30 seconds

    return () => clearInterval(healthCheckInterval);
  }, [connectionStatus, setConnectionStatus, setTracks]);

  // Connection status indicator
  const ConnectionStatus = () => {
    const getStatusConfig = () => {
      switch (connectionStatus) {
        case 'connected':
          return {
            icon: <CheckCircle className="w-4 h-4 text-green-500" />,
            text: 'Connected',
            className: 'text-green-700 bg-green-50 border-green-200'
          };
        case 'error':
          return {
            icon: <WifiOff className="w-4 h-4 text-red-500" />,
            text: 'Disconnected',
            className: 'text-red-700 bg-red-50 border-red-200'
          };
        default:
          return {
            icon: <Loader className="w-4 h-4 text-yellow-500 animate-spin" />,
            text: 'Connecting...',
            className: 'text-yellow-700 bg-yellow-50 border-yellow-200'
          };
      }
    };

    const config = getStatusConfig();

    return (
      <div className={`flex items-center gap-2 px-3 py-1 rounded-md border text-sm ${config.className}`}>
        {config.icon}
        <span>{config.text}</span>
      </div>
    );
  };

  // Error banner
  const ErrorBanner = () => {
    if (!error) return null;

    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
        <div className="flex items-center gap-2">
          <AlertCircle className="w-5 h-5 text-red-500 flex-shrink-0" />
          <div>
            <h3 className="text-red-800 font-medium">Connection Error</h3>
            <p className="text-red-700 text-sm mt-1">{error}</p>
            <button
              onClick={() => window.location.reload()}
              className="text-red-700 underline text-sm mt-2 hover:text-red-800"
            >
              Reload page
            </button>
          </div>
        </div>
      </div>
    );
  };

  // Loading screen
  if (isLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <Loader className="w-8 h-8 text-indigo-600 animate-spin mx-auto mb-4" />
          <h2 className="text-lg font-medium text-gray-900 mb-2">
            Loading Flow Engine Debug UI
          </h2>
          <p className="text-gray-600">Connecting to backend...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 px-6 py-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-4">
            <h1 className="text-xl font-semibold text-gray-900">
              Flow Engine Debug UI
            </h1>
            <ConnectionStatus />
          </div>
          <div className="text-sm text-gray-500">
            Enhanced with Template Support & Variable Placeholders
          </div>
        </div>
        <ErrorBanner />
      </header>

      {/* Main layout */}
      <div className="flex-1 flex overflow-hidden">
        {/* Left Panel - Track Browser */}
        <div 
          className="bg-white border-r border-gray-200 flex-shrink-0 overflow-hidden"
          style={{ width: leftPanelWidth }}
        >
          <TrackBrowser />
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          {/* Canvas Area */}
          <div 
            className="flex-1 overflow-hidden"
            style={{ 
              height: showBottomPanel 
                ? `calc(100% - ${bottomPanelHeight}px)` 
                : '100%' 
            }}
          >
            <FlowCanvas />
          </div>

          {/* Bottom Panel - Execution Controls */}
          {showBottomPanel && (
            <div 
              className="border-t border-gray-200 bg-white flex-shrink-0"
              style={{ height: bottomPanelHeight }}
            >
              <ExecutionControls />
            </div>
          )}
        </div>

        {/* Right Panel - Debug Information */}
        <div 
          className="bg-white border-l border-gray-200 flex-shrink-0 overflow-hidden"
          style={{ width: rightPanelWidth }}
        >
          <DebugPanel />
        </div>
      </div>
    </div>
  );
}

export default App; 