import axios from 'axios';

const API_BASE_URL = 'http://127.0.0.1:5000';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  withCredentials: true,
});

// Request interceptor for authentication
api.interceptors.request.use(
  (config) => {
    // Add session token from localStorage if available
    const sessionToken = localStorage.getItem('session_token');
    if (sessionToken) {
      config.headers['X-Session-Token'] = sessionToken;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor for handling errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Let React Router and AuthContext handle 401 errors
    // Don't automatically redirect here to avoid loops
    return Promise.reject(error);
  }
);

// Authentication API
export const authAPI = {
  login: (licenseKey: string) =>
    api.post('/auth/login', { license_key: licenseKey }),

  logout: () =>
    api.post('/auth/logout'),

  validateSession: () =>
    api.get('/auth/validate'),

  getLicenseTiers: () =>
    api.get('/license/tiers'),
};

// Analysis API
export const analysisAPI = {
  getSentiment: (symbol: string, articles: number = 20) =>
    api.get(`/sentiment?symbol=${symbol}&articles=${articles}`),

  getTechnical: (symbol: string, timeframe: string = 'hour') =>
    api.get(`/technical?symbol=${symbol}&timeframe=${timeframe}`),

  getUnified: (symbol: string, articles: number = 20, saveOutput: boolean = false) =>
    api.get(`/unified?symbol=${symbol}&articles=${articles}&save_output=${saveOutput}`),

  getIndustry: (symbol: string, forceRefresh: boolean = false) =>
    api.get(`/industry?symbol=${symbol}&force_refresh=${forceRefresh}`),

  getHistorical: (symbol: string, startDate: string, endDate: string) =>
    api.get(`/historical?symbol=${symbol}&start_date=${startDate}&end_date=${endDate}`),

  getCurrent: (symbol: string) =>
    api.get(`/current?symbol=${symbol}`),

  getMacro: (symbol: string, daysBack: number = 7) =>
    api.get(`/macro?symbol=${symbol}&days_back=${daysBack}`),

  getSector: (sector: string, daysBack: number = 7) =>
    api.get(`/sector?sector=${sector}&days_back=${daysBack}`),
};

export default api;