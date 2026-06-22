/**
 * services/api.js
 * ===============
 * Unified Axios API Client Configuration
 * 
 * WHY THIS FILE EXISTS:
 *     Instead of importing axios and specifying base URLs or headers on every page,
 *     we configure a central axios instance. This acts as our network gateway,
 *     injecting credentials and handling errors uniformly.
 */

import axios from 'axios';

// Create a configured instance of Axios
const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || "https://aether-noc-backend.onrender.com",
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request Interceptor: Attach JWT bearer token to every request if it exists
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response Interceptor: Catch auth errors (e.g., expired token) and route to logout
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Clear credentials on unauthorized/expired responses
      localStorage.removeItem('token');
      localStorage.removeItem('user');

      // Optionally redirect to login page (can also be handled inside the React context)
      if (!window.location.pathname.includes('/login') && !window.location.pathname.includes('/register')) {
        window.location.href = '/login?expired=true';
      }
    }
    return Promise.reject(error);
  }
);

export default api;
