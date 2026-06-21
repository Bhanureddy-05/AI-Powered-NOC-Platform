/**
 * services/alerts.js
 * ==================
 * Alert Engine API Client Service
 */

import api from './api';

export const alertsService = {
  /**
   * Fetches paginated alert list matching optional filters.
   * 
   * @param {object} params - { status, severity, device_id, page, size }
   */
  async getAlerts(params = {}) {
    const response = await api.get('/alerts/', { params });
    return response.data; // Returns { alerts: [...], total, page, size, pages }
  },

  /**
   * Fetches general statistics of alerts (totals by severity and state).
   */
  async getAlertStats() {
    const response = await api.get('/alerts/stats');
    return response.data; // Returns stats count mapping
  },

  /**
   * Fetches details of a specific alert by its UUID.
   * 
   * @param {string} id - Alert UUID
   */
  async getAlertById(id) {
    const response = await api.get(`/alerts/${id}`);
    return response.data;
  },

  /**
   * Fetches the transition history log of an alert.
   * 
   * @param {string} id - Alert UUID
   */
  async getAlertHistory(id) {
    const response = await api.get(`/alerts/${id}/history`);
    return response.data; // Returns list of history records
  },

  /**
   * Acknowledges an active alert.
   * 
   * @param {string} id - Alert UUID
   * @param {string} notes - Verification or initial debugging remarks
   */
  async acknowledgeAlert(id, notes = '') {
    const response = await api.patch(`/alerts/${id}/acknowledge`, { notes });
    return response.data;
  },

  /**
   * Resolves a corrected alert.
   * 
   * @param {string} id - Alert UUID
   * @param {string} notes - Summary of actions performed to fix the issue
   */
  async resolveAlert(id, notes = '') {
    const response = await api.patch(`/alerts/${id}/resolve`, { notes });
    return response.data;
  },
};

export default alertsService;
