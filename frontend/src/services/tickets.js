/**
 * services/tickets.js
 * ===================
 * Incident Tickets API Client Service
 */

import api from './api';

export const ticketsService = {
  /**
   * Fetches incident tickets list filterable by state, priority, and assignee.
   * 
   * @param {object} params - { status, priority, assigned_to, device_id, page, size }
   */
  async getTickets(params = {}) {
    const response = await api.get('/tickets/', { params });
    return response.data; // Returns { tickets: [...], total, page, size, pages }
  },

  /**
   * Fetches statistics summary of tickets.
   */
  async getTicketStats() {
    const response = await api.get('/tickets/stats');
    return response.data;
  },

  /**
   * Fetches a specific ticket record by UUID.
   * 
   * @param {string} id - Ticket UUID
   */
  async getTicketById(id) {
    const response = await api.get(`/tickets/${id}`);
    return response.data;
  },

  /**
   * Submits a new incident ticket.
   * 
   * @param {object} payload - { device_id, alert_id, title, description, priority, severity, assigned_to }
   */
  async createTicket(payload) {
    const response = await api.post('/tickets/', payload);
    return response.data;
  },

  /**
   * Updates fields (status, assignee, priority) of a ticket.
   * 
   * @param {string} id - Ticket UUID
   * @param {object} payload - { title, description, status, priority, severity, assigned_to, sla_status }
   */
  async updateTicket(id, payload) {
    const response = await api.put(`/tickets/${id}`, payload);
    return response.data;
  },

  /**
   * Appends an investigative comment log to the ticket.
   * 
   * @param {string} ticketId - Ticket UUID
   * @param {string} comment - Comment text markdown
   */
  async addComment(ticketId, comment) {
    const response = await api.post(`/tickets/${ticketId}/comments`, { comment });
    return response.data;
  },

  /**
   * Fetches comment history logs for a ticket.
   * 
   * @param {string} ticketId - Ticket UUID
   */
  async getComments(ticketId) {
    const response = await api.get(`/tickets/${ticketId}/comments`);
    return response.data;
  },

  /**
   * Fetches lifecycle modifications log for a ticket.
   * 
   * @param {string} ticketId - Ticket UUID
   */
  async getTicketHistory(ticketId) {
    const response = await api.get(`/tickets/${ticketId}/history`);
    return response.data;
  },
};

export default ticketsService;
