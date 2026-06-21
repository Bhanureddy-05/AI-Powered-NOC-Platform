/**
 * services/reports.js
 * ===================
 * Reports & Exports API Client Service
 */

import api from './api';

export const reportsService = {
  /**
   * Fetches the system-wide operations aggregates.
   * 
   * @param {number} days - Time window in days
   */
  async getReportSummary(days = 7) {
    const response = await api.get('/reports/summary', { params: { days } });
    return response.data;
  },

  /**
   * Triggers a browser file download of a CSV spreadsheet or compiled PDF.
   * 
   * @param {string} type - Export target (metrics, alerts, tickets)
   * @param {string} format - File extension (csv, pdf)
   * @param {number} days - Time window in days
   */
  async downloadReport(type, format, days = 7) {
    const targetFormat = format.toLowerCase();
    
    if (targetFormat === 'csv') {
      const response = await api.get('/reports/csv', {
        params: { type, days },
        responseType: 'blob',
      });
      this._triggerDownload(response.data, `noc_export_${type}_${days}d.csv`);
    } else if (targetFormat === 'pdf') {
      const response = await api.get('/reports/pdf', {
        params: { days },
        responseType: 'blob',
      });
      this._triggerDownload(response.data, `noc_report_${days}d.pdf`);
    }
  },

  /**
   * Browser file download utility helper.
   */
  _triggerDownload(blobData, filename) {
    const url = window.URL.createObjectURL(new Blob([blobData]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
};

export default reportsService;
