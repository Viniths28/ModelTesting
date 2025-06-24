import axios from 'axios';

// Create axios instance with default config
const api = axios.create({
  baseURL: 'http://localhost:8001',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`🚀 API Request: ${config.method?.toUpperCase()} ${config.url}`, config.data);
    return config;
  },
  (error) => {
    console.error('❌ API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for logging and error handling
api.interceptors.response.use(
  (response) => {
    console.log(`✅ API Response: ${response.config.method?.toUpperCase()} ${response.config.url}`, response.data);
    return response;
  },
  (error) => {
    console.error(`❌ API Response Error: ${error.config?.method?.toUpperCase()} ${error.config?.url}`, {
      status: error.response?.status,
      data: error.response?.data,
      message: error.message
    });
    return Promise.reject(error);
  }
);

// API functions
export const debugApi = {
  // Health check
  async healthCheck() {
    const response = await api.get('/api/health');
    return response.data;
  },

  // Execute debug flow with isPrimaryFlow parameter
  async executeDebugFlow(payload) {
    const response = await api.post('/api/execute', payload);
    return response.data;
  },

  // Track management
  async getTracks() {
    const response = await api.get('/api/tracks');
    return response.data;
  },

  async recordTrackAccess(trackId, sectionId = null) {
    const response = await api.post('/api/tracks/access', {
      track_id: trackId,
      section_id: sectionId
    });
    return response.data;
  },

  async getRecentTracks() {
    const response = await api.get('/api/tracks/recent');
    return response.data;
  },

  // Section details
  async getSectionDetails(sectionId) {
    const response = await api.get(`/api/sections/${sectionId}`);
    return response.data;
  },

  // Execution history
  async getExecutionHistory(limit = 50) {
    const response = await api.get(`/api/history?limit=${limit}`);
    return response.data;
  },

  async getFavorites() {
    const response = await api.get('/api/favorites');
    return response.data;
  },

  async toggleFavorite(executionId) {
    const response = await api.post('/api/favorites/toggle', {
      execution_id: executionId
    });
    return response.data;
  },

  async updateExecutionName(executionId, name) {
    const response = await api.post('/api/executions/update-name', {
      execution_id: executionId,
      name: name
    });
    return response.data;
  }
};

// Error handler utility
export const handleApiError = (error, defaultMessage = 'An error occurred') => {
  if (error.response) {
    // Server responded with error status
    const status = error.response.status;
    const data = error.response.data;
    
    if (status === 404) {
      return 'Resource not found';
    } else if (status === 500) {
      return data?.detail?.error || data?.detail || 'Internal server error';
    } else if (status === 409) {
      return data?.detail?.message || 'Conflict error';
    } else {
      return data?.detail || data?.message || `HTTP ${status} error`;
    }
  } else if (error.request) {
    // Request made but no response
    return 'Unable to connect to server. Please check if the backend is running.';
  } else {
    // Something else happened
    return error.message || defaultMessage;
  }
};

// Connection test utility
export const testConnection = async () => {
  try {
    await debugApi.healthCheck();
    return { success: true, message: 'Connected successfully' };
  } catch (error) {
    return { 
      success: false, 
      message: handleApiError(error, 'Failed to connect to backend')
    };
  }
};

export default api; 