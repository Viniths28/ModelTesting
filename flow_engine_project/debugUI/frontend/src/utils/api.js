import axios from 'axios';

// Configure axios defaults
const api = axios.create({
  baseURL: 'http://localhost:8005',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('API Request Error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    console.error('API Response Error:', error.response?.data || error.message);
    
    // Handle specific error cases
    if (error.response?.status === 404) {
      console.warn('Resource not found');
    } else if (error.response?.status >= 500) {
      console.error('Server error occurred');
    }
    
    return Promise.reject(error);
  }
);

// API helper functions
export const apiHelpers = {
  // Track and Section APIs
  async getTracks() {
    const response = await api.get('/api/tracks');
    return response.data;
  },

  async recordTrackAccess(trackId, trackName) {
    const response = await api.post('/api/tracks/access', {
      trackId,
      trackName
    });
    return response.data;
  },

  async getRecentTracks() {
    const response = await api.get('/api/tracks/recent');
    return response.data;
  },

  async getSectionInfo(sectionId) {
    const response = await api.get(`/api/sections/${sectionId}/info`);
    return response.data;
  },

  // Execution APIs
  async executeFlow(payload, executionName = null) {
    const requestData = {
      ...payload,
      executionName: executionName || `Execution ${new Date().toLocaleTimeString()}`
    };
    
    const response = await api.post('/api/execute', requestData);
    return response.data;
  },

  // History and Favorites APIs
  async getExecutionHistory(limit = 50) {
    const response = await api.get('/api/history', {
      params: { limit }
    });
    return response.data;
  },

  async getFavorites() {
    const response = await api.get('/api/favorites');
    return response.data;
  },

  async toggleFavorite(executionId) {
    const response = await api.post(`/api/history/${executionId}/favorite`);
    return response.data;
  },

  async updateExecutionName(executionId, name) {
    const response = await api.patch(`/api/history/${executionId}/name`, {
      name
    });
    return response.data;
  },

  // Health check
  async healthCheck() {
    const response = await api.get('/health');
    return response.data;
  }
};

// Export default api instance
export default api; 