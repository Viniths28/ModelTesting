import React, { useState, useEffect } from 'react';
import { ChevronRight, ChevronDown, Folder, FileText, Clock, Search } from 'lucide-react';
import { useDebugStore } from '../store/debugStore';
import { apiHelpers } from '../utils/api';

const TrackBrowser = () => {
  const {
    tracks,
    selectedTrack,
    selectedSection,
    recentTracks,
    setTracks,
    setSelectedTrack,
    setSelectedSection
  } = useDebugStore();
  
  const [expandedTracks, setExpandedTracks] = useState(new Set());
  const [searchTerm, setSearchTerm] = useState('');
  const [loading, setLoading] = useState(false);

  // Load tracks on component mount
  useEffect(() => {
    loadTracks();
  }, []);

  const loadTracks = async () => {
    setLoading(true);
    try {
      const tracksData = await apiHelpers.getTracks();
      setTracks(tracksData);
      
      // Auto-expand selected track
      if (selectedTrack) {
        setExpandedTracks(prev => new Set([...prev, selectedTrack.trackId]));
      }
    } catch (error) {
      console.error('Failed to load tracks:', error);
    } finally {
      setLoading(false);
    }
  };

  const toggleTrackExpansion = (trackId) => {
    setExpandedTracks(prev => {
      const newSet = new Set(prev);
      if (newSet.has(trackId)) {
        newSet.delete(trackId);
      } else {
        newSet.add(trackId);
      }
      return newSet;
    });
  };

  const handleTrackSelect = async (track) => {
    setSelectedTrack(track);
    setExpandedTracks(prev => new Set([...prev, track.trackId]));
    
    // Record track access
    try {
      await apiHelpers.recordTrackAccess(track.trackId, track.trackName);
    } catch (error) {
      console.error('Failed to record track access:', error);
    }
  };

  const handleSectionSelect = (section) => {
    setSelectedSection(section);
  };

  const filteredTracks = tracks.filter(track => 
    track.trackName.toLowerCase().includes(searchTerm.toLowerCase()) ||
    track.sections.some(section => 
      section.sectionName.toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <h2 className="text-lg font-semibold text-gray-900 mb-3">Track Browser</h2>
        
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <input
            type="text"
            placeholder="Search tracks and sections..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {/* Recent Tracks */}
      {recentTracks.length > 0 && (
        <div className="p-4 border-b border-gray-200">
          <div className="flex items-center mb-2">
            <Clock className="w-4 h-4 text-gray-500 mr-2" />
            <h3 className="text-sm font-medium text-gray-700">Recent</h3>
          </div>
          <div className="space-y-1">
            {recentTracks.slice(0, 3).map((track) => (
              <button
                key={track.trackId}
                onClick={() => handleTrackSelect(track)}
                className="w-full text-left px-2 py-1 text-sm text-gray-600 hover:bg-gray-100 rounded"
              >
                {track.trackName}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Track List */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="p-4 text-center">
            <div className="spinner w-6 h-6 mx-auto mb-2"></div>
            <p className="text-sm text-gray-500">Loading tracks...</p>
          </div>
        ) : filteredTracks.length === 0 ? (
          <div className="p-4 text-center text-gray-500">
            <p className="text-sm">No tracks found</p>
          </div>
        ) : (
          <div className="p-2">
            {filteredTracks.map((track) => (
              <div key={track.trackId} className="mb-2">
                {/* Track Header */}
                <div
                  className={`track-item flex items-center p-2 rounded cursor-pointer ${
                    selectedTrack?.trackId === track.trackId ? 'active' : ''
                  }`}
                  onClick={() => handleTrackSelect(track)}
                >
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleTrackExpansion(track.trackId);
                    }}
                    className="mr-2 p-1 hover:bg-gray-200 rounded"
                  >
                    {expandedTracks.has(track.trackId) ? (
                      <ChevronDown className="w-4 h-4" />
                    ) : (
                      <ChevronRight className="w-4 h-4" />
                    )}
                  </button>
                  
                  <Folder className="w-4 h-4 mr-2 text-blue-600" />
                  
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-900 truncate">
                      {track.trackName}
                    </p>
                    <p className="text-xs text-gray-500">
                      {track.sections.length} section{track.sections.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                </div>

                {/* Sections */}
                {expandedTracks.has(track.trackId) && (
                  <div className="ml-6 mt-1 space-y-1">
                    {track.sections.map((section) => (
                      <div
                        key={section.sectionId}
                        className={`section-item flex items-center p-2 rounded cursor-pointer ${
                          selectedSection?.sectionId === section.sectionId 
                            ? 'bg-blue-50 text-blue-800' 
                            : 'hover:bg-gray-50'
                        }`}
                        onClick={() => handleSectionSelect(section)}
                      >
                        <FileText className="w-3 h-3 mr-2 text-gray-500" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm truncate">{section.sectionName}</p>
                          {section.variables && section.variables.length > 0 && (
                            <p className="text-xs text-gray-500">
                              {section.variables.length} variable{section.variables.length !== 1 ? 's' : ''}
                            </p>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-gray-200 bg-gray-50">
        <button
          onClick={loadTracks}
          disabled={loading}
          className="w-full px-3 py-2 text-sm text-gray-600 hover:text-gray-800 hover:bg-gray-100 rounded disabled:opacity-50"
        >
          {loading ? 'Refreshing...' : 'Refresh Tracks'}
        </button>
      </div>
    </div>
  );
};

export default TrackBrowser; 