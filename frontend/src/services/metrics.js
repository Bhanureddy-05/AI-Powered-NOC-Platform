/**
 * services/metrics.js
 * ===================
 * Telemetry Metrics API Client Service
 * 
 * WHY THIS FILE EXISTS:
 *     Connects React components (such as future charts and stats widgets)
 *     to our time-series metrics data store. It handles query parameters
 *     for history search.
 */

import api from './api';

export const metricsService = {
  /**
   * Pushes a new telemetry measurement to the backend database.
   * Typically called by administrative tools or edge simulation daemons.
   */
  async ingestMetric(metricData) {
    const response = await api.post('/metrics/', metricData);
    return response.data;
  },

  /**
   * Retrieves historical telemetry records for a specific device.
   * Useful for plotting time-series charts (e.g. CPU or Memory trends).
   * 
   * @param {string} deviceId - Target device UUID
   * @param {object} params - Optional query filters: { start_time, end_time, limit }
   */
  async getMetricHistory(deviceId, params = {}) {
    const response = await api.get(`/metrics/${deviceId}`, { params });
    return response.data; // Returns a list of metric data points sorted by timestamp
  },
};

export default metricsService;
