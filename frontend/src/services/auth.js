/**
 * services/auth.js
 * ================
 * Authentication Endpoint Wrapper functions
 * 
 * WHY THIS FILE EXISTS:
 *     This abstracts endpoints into asynchronous JavaScript actions.
 *     React pages call these functions rather than making raw axios requests,
 *     keeping UI code separate from API path structures.
 */

import api from './api';

export const authService = {
  /**
   * authenticates credentials and returns JWT token.
   */
  async login(username, password) {
    const response = await api.post('/api/v1/auth/login', { username, password });
    return response.data; // { access_token: "...", token_type: "bearer" }
  },

  /**
   * registers a new NOC operations user.
   */
  async register(username, email, password, role = 'operator') {
    const response = await api.post('/api/v1/auth/register', {
      username,
      email,
      password,
      role,
    });
    return response.data; // { id: 1, username: "...", email: "...", role: "..." }
  },

  /**
   * fetches active profile based on token.
   */
  async getMe() {
    const response = await api.get('/api/v1/auth/me');
    return response.data;
  },
};
export default authService;
