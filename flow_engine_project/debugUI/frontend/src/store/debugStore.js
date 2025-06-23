import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useDebugStore = create(
  persist(
    (set, get) => ({
      // Track and Section Selection
      tracks: [],
      selectedTrack: null,
      selectedSection: null,
      recentTracks: [],
      
      // Execution State
      executionResult: null,
      debugInfo: null,
      isExecuting: false,
      executionHistory: [],
      favorites: [],
      
      // UI State
      canvasData: null,
      selectedNode: null,
      
      // JSON Editor State
      currentPayload: {
        sectionId: '',
        applicationId: 'app_123',
        applicantId: 'applicant_456',
        isPrimaryFlow: true
      },
      
      // Actions
      setTracks: (tracks) => set({ tracks }),
      
      setSelectedTrack: (track) => {
        set({ selectedTrack: track, selectedSection: null });
        
        // Add to recent tracks
        const { recentTracks } = get();
        const updated = [track, ...recentTracks.filter(t => t.trackId !== track.trackId)].slice(0, 5);
        set({ recentTracks: updated });
      },
      
      setSelectedSection: (section) => {
        set({ 
          selectedSection: section,
          currentPayload: {
            ...get().currentPayload,
            sectionId: section?.sectionId || ''
          }
        });
      },
      
      setExecutionResult: (result, debugInfo) => {
        set({ 
          executionResult: result, 
          debugInfo,
          isExecuting: false 
        });
        
        // Add to execution history
        const { executionHistory } = get();
        const execution = {
          id: Date.now(),
          timestamp: new Date().toISOString(),
          sectionId: result.sectionId,
          payload: get().currentPayload,
          result,
          debugInfo,
          name: `${get().selectedSection?.sectionName || 'Unknown'} - ${new Date().toLocaleTimeString()}`
        };
        
        set({ 
          executionHistory: [execution, ...executionHistory.slice(0, 49)] // Keep last 50
        });
      },
      
      setIsExecuting: (isExecuting) => set({ isExecuting }),
      
      setCurrentPayload: (payload) => set({ currentPayload: payload }),
      
      updatePayloadField: (field, value) => {
        const { currentPayload } = get();
        set({ 
          currentPayload: { 
            ...currentPayload, 
            [field]: value 
          }
        });
      },
      
      setCanvasData: (data) => set({ canvasData: data }),
      
      setSelectedNode: (node) => set({ selectedNode: node }),
      
      addToFavorites: (execution) => {
        const { favorites } = get();
        const favorite = {
          ...execution,
          id: Date.now(),
          addedAt: new Date().toISOString()
        };
        set({ favorites: [favorite, ...favorites] });
      },
      
      removeFromFavorites: (id) => {
        const { favorites } = get();
        set({ favorites: favorites.filter(f => f.id !== id) });
      },
      
      replayExecution: (execution) => {
        set({ 
          currentPayload: execution.payload,
          selectedSection: { sectionId: execution.sectionId }
        });
      },
      
      clearExecution: () => {
        set({ 
          executionResult: null, 
          debugInfo: null, 
          canvasData: null,
          selectedNode: null 
        });
      },
      
      // Load initial data
      loadTracks: async () => {
        try {
          const response = await fetch('/api/tracks');
          const tracks = await response.json();
          set({ tracks });
        } catch (error) {
          console.error('Failed to load tracks:', error);
        }
      },
      
      loadExecutionHistory: async () => {
        try {
          const response = await fetch('/api/history');
          const history = await response.json();
          set({ executionHistory: history });
        } catch (error) {
          console.error('Failed to load execution history:', error);
        }
      },
      
      loadFavorites: async () => {
        try {
          const response = await fetch('/api/favorites');
          const favorites = await response.json();
          set({ favorites });
        } catch (error) {
          console.error('Failed to load favorites:', error);
        }
      },
      
      addExecutionHistoryItem: (item) => {
        const { executionHistory } = get();
        set({ executionHistory: [item, ...executionHistory.slice(0, 49)] });
      }
    }),
    {
      name: 'debug-store',
      partialize: (state) => ({
        selectedTrack: state.selectedTrack,
        selectedSection: state.selectedSection,
        recentTracks: state.recentTracks,
        currentPayload: state.currentPayload,
        favorites: state.favorites
      })
    }
  )
); 