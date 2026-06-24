/**
 * services/metrics.js
 * ===================
 * Telemetry Metrics API Client Service
 *
 * WHY THIS FILE EXISTS:
 *     Connects React components to our time-series metrics data store.
 *     Handles ingestion, history queries, system metrics (psutil), and stats.
 */

import api from './api';

export const metricsService = {
  /**
   * Pushes a new telemetry measurement to the backend database.
   * Typically called by admin tools or edge simulation agents.
   */
  async ingestMetric(metricData) {
    const response = await api.post('/metrics/', metricData);
    return response.data;
  },

  /**
   * Retrieves historical telemetry records for a specific device.
   * Used to plot time-series CPU, memory, latency, and bandwidth charts.
   *
   * @param {string} deviceId - Target device UUID
   * @param {object} params   - Optional filters: { start_time, end_time, limit }
   */
  async getMetricHistory(deviceId, params = {}) {
    const response = await api.get(`/metrics/${deviceId}`, { params });
    return response.data;
  },

  /**
   * Returns real-time host system metrics collected by psutil.
   * Exposes CPU %, memory, disk, and network I/O from the backend server.
   */
  async getSystemMetrics() {
    const response = await api.get('/metrics/system');
    return response.data;
  },

  /**
   * Returns aggregate statistics across all devices for the past N hours.
   * Used by the dashboard KPI cards and summary panels.
   *
   * @param {number} hours - Time window in hours (1–168)
   */
  async getStats(hours = 1) {
    const response = await api.get('/metrics/stats', { params: { hours } });
    return response.data;
  },
};

export default metricsService;
