/**
 * services/audit.js
 * ==================
 * Security Auditing & Activity Tracking Client Service
 */

import api from './api';

export const auditService = {
  /**
   * Fetches paginated activity log trail (Admin only).
   * 
   * @param {object} params - { username, action, ip_address, page, size }
   */
  async getAuditLogs(params = {}) {
    const response = await api.get('/audit/', { params });
    return response.data; // Returns { logs: [...], total, page, size, pages }
  },

  /**
   * Fetches audit log aggregates and category counts (Admin only).
   */
  async getAuditLogStats() {
    const response = await api.get('/audit/stats');
    return response.data; // Returns AuditLogStatsResponse
  },
};

export default auditService;
