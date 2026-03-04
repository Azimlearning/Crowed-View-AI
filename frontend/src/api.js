import axios from 'axios';

// Use relative URL so Vite proxy (vite.config.js) forwards /api to backend:8000
const API_BASE_URL = import.meta.env.DEV ? '' : 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 10000, // 10 second timeout
});

// Retry logic with exponential backoff
const retryRequest = async (requestFn, maxRetries = 3, delay = 1000) => {
  for (let i = 0; i < maxRetries; i++) {
    try {
      return await requestFn();
    } catch (error) {
      if (i === maxRetries - 1) throw error;
      // Exponential backoff: 1s, 2s, 4s
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)));
    }
  }
};

export const getSeats = async () => {
  try {
    const response = await retryRequest(() => api.get('/api/seats'));
    return response.data.seats;
  } catch (error) {
    if (error.response) {
      throw new Error(`Server error: ${error.response.status} - ${error.response.data?.detail || 'Unknown error'}`);
    } else if (error.request) {
      throw new Error('Network error: Could not reach the backend server. Make sure it is running on http://localhost:8000');
    } else {
      throw new Error(`Request error: ${error.message}`);
    }
  }
};

export const getZones = async () => {
  try {
    const response = await retryRequest(() => api.get('/api/zones'));
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(`Server error: ${error.response.status} - ${error.response.data?.detail || 'Unknown error'}`);
    } else if (error.request) {
      throw new Error('Network error: Could not reach the backend server.');
    } else {
      throw new Error(`Request error: ${error.message}`);
    }
  }
};

export const getSuggestions = async (zoneName) => {
  try {
    const response = await retryRequest(() => api.post('/api/suggestions', { zone_name: zoneName }));
    return response.data;
  } catch (error) {
    if (error.response) {
      const status = error.response.status;
      if (status === 404) {
        throw new Error(`Zone '${zoneName}' not found`);
      } else if (status === 500) {
        throw new Error(`AI service error: ${error.response.data?.detail || 'Failed to generate suggestions'}`);
      } else {
        throw new Error(`Server error: ${status} - ${error.response.data?.detail || 'Unknown error'}`);
      }
    } else if (error.request) {
      throw new Error('Network error: Could not reach the backend server.');
    } else {
      throw new Error(`Request error: ${error.message}`);
    }
  }
};

export const getConfig = async () => {
  try {
    const response = await api.get('/api/config');
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(`Server error: ${error.response.status} - ${error.response.data?.detail || 'Unknown error'}`);
    } else if (error.request) {
      throw new Error('Network error: Could not reach the backend server.');
    } else {
      throw new Error(`Request error: ${error.message}`);
    }
  }
};

export const updateConfig = async (configUpdate) => {
  try {
    const response = await api.post('/api/config', configUpdate);
    return response.data;
  } catch (error) {
    if (error.response) {
      throw new Error(`Server error: ${error.response.status} - ${error.response.data?.detail || 'Unknown error'}`);
    } else if (error.request) {
      throw new Error('Network error: Could not reach the backend server.');
    } else {
      throw new Error(`Request error: ${error.message}`);
    }
  }
};

export default api;
