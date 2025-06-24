import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';

const useDebugStore = create(
  persist(
    (set, get) => ({
      // Connection state
      connectionStatus: 'disconnected', // connected, disconnected, error
      backendUrl: 'http://localhost:8001',
      
      // Track and section data
      tracks: [],
      selectedTrack: null,
      selectedSection: null,
      sectionDetails: null,
      
      // Execution state
      isExecuting: false,
      executionResult: null,
      executionHistory: [],
      favorites: [],
      
      // UI state
      leftPanelWidth: 300,
      rightPanelWidth: 300,
      bottomPanelHeight: 250,
      showBottomPanel: true,
      selectedNode: null,
      selectedStep: null,
      
      // Debug panel tabs
      debugActiveTab: 'variables', // variables, conditions, sourceNodes
      
      // JSON payload state
      jsonPayload: {
        sectionId: '',
        applicationId: 'app_12345',
        applicantId: 'applicant_67890',
        isPrimaryFlow: true
      },
      
      // Actions
      setConnectionStatus: (status) => set({ connectionStatus: status }),
      
      setTracks: (tracks) => set({ tracks }),
      
      setSelectedTrack: (track) => set({ 
        selectedTrack: track,
        selectedSection: null,
        sectionDetails: null 
      }),
      
      setSelectedSection: (section) => set({ 
        selectedSection: section,
        jsonPayload: {
          ...get().jsonPayload,
          sectionId: section?.sectionId || ''
        }
      }),
      
      setSectionDetails: (details) => set({ sectionDetails: details }),
      
      setExecuting: (isExecuting) => set({ isExecuting }),
      
      setExecutionResult: (result) => set({ 
        executionResult: result,
        selectedNode: null,
        selectedStep: null
      }),
      
      setExecutionHistory: (history) => set({ executionHistory: history }),
      
      setFavorites: (favorites) => set({ favorites }),
      
      // UI state actions
      setLeftPanelWidth: (width) => set({ leftPanelWidth: width }),
      
      setRightPanelWidth: (width) => set({ rightPanelWidth: width }),
      
      setBottomPanelHeight: (height) => set({ bottomPanelHeight: height }),
      
      setShowBottomPanel: (show) => set({ showBottomPanel: show }),
      
      setSelectedNode: (node) => set({ selectedNode: node }),
      
      setSelectedStep: (step) => set({ selectedStep: step }),
      
      setDebugActiveTab: (tab) => set({ debugActiveTab: tab }),
      
      // JSON payload actions
      updateJsonPayload: (updates) => set({ 
        jsonPayload: { ...get().jsonPayload, ...updates }
      }),
      
      setJsonPayload: (payload) => set({ jsonPayload: payload }),
      
      // Auto-populate sectionId when section is selected
      autoPopulateSectionId: () => {
        const { selectedSection, jsonPayload } = get();
        if (selectedSection && !jsonPayload.sectionId) {
          set({
            jsonPayload: {
              ...jsonPayload,
              sectionId: selectedSection.sectionId
            }
          });
        }
      },
      
      // Clear execution state
      clearExecution: () => set({
        executionResult: null,
        selectedNode: null,
        selectedStep: null,
        isExecuting: false
      }),
      
      // Panel visibility helpers
      toggleBottomPanel: () => set({ showBottomPanel: !get().showBottomPanel }),
      
      // History management
      addToHistory: (execution) => {
        const history = get().executionHistory;
        set({ 
          executionHistory: [execution, ...history].slice(0, 100) // Keep last 100
        });
      },
      
      toggleFavorite: (executionId) => {
        const favorites = get().favorites;
        const isFavorite = favorites.some(f => f.id === executionId);
        
        if (isFavorite) {
          set({ 
            favorites: favorites.filter(f => f.id !== executionId)
          });
        } else {
          const history = get().executionHistory;
          const execution = history.find(h => h.id === executionId);
          if (execution) {
            set({ 
              favorites: [execution, ...favorites]
            });
          }
        }
      },
      
      // Reset store
      reset: () => set({
        tracks: [],
        selectedTrack: null,
        selectedSection: null,
        sectionDetails: null,
        executionResult: null,
        selectedNode: null,
        selectedStep: null,
        isExecuting: false
      })
    }),
    {
      name: 'debug-ui-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        // Persist UI preferences and JSON payload
        leftPanelWidth: state.leftPanelWidth,
        rightPanelWidth: state.rightPanelWidth,
        bottomPanelHeight: state.bottomPanelHeight,
        showBottomPanel: state.showBottomPanel,
        debugActiveTab: state.debugActiveTab,
        jsonPayload: state.jsonPayload,
        backendUrl: state.backendUrl,
        // Don't persist execution state or tracks (reload fresh)
      })
    }
  )
);

export default useDebugStore; 