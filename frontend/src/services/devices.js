/**
 * services/devices.js
 * ===================
 * Device Inventory API Client Service
 * 
 * WHY THIS FILE EXISTS:
 *     Encapsulates all server calls targeting device resource routers.
 *     Allows components to query, register, edit, and delete network devices
 *     using standardized async functions rather than composing raw network calls.
 */

import api from './api';

export const devicesService = {
  /**
   * Fetches paginated device list matching optional filter parameters.
   * 
   * @param {object} params - Optional parameters: { q, device_type, status, page, size }
   */
  async getDevices(params = {}) {
    const response = await api.get('/devices/', { params });
    return response.data; // Returns { devices: [...], total, page, size, pages }
  },

  /**
   * Fetches details of a specific device by its UUID.
   * 
   * @param {string} id - Device UUID
   */
  async getDeviceById(id) {
    const response = await api.get(`/devices/${id}`);
    return response.data; // Returns DeviceResponse
  },

  /**
   * Registers a new device in the inventory.
   * 
   * @param {object} payload - Device details: { device_name, ip_address, location, device_type, status }
   */
  async createDevice(payload) {
    const response = await api.post('/devices/', payload);
    return response.data; // Returns DeviceResponse
  },

  /**
   * Updates metadata of a registered device.
   * 
   * @param {string} id - Device UUID
   * @param {object} payload - Fields to update: { device_name, ip_address, location, device_type, status }
   */
  async updateDevice(id, payload) {
    const response = await api.put(`/devices/${id}`, payload);
    return response.data; // Returns DeviceResponse
  },

  /**
   * Deletes a device from the database inventory (Admin only).
   * 
   * @param {string} id - Device UUID
   */
  async deleteDevice(id) {
    const response = await api.delete(`/devices/${id}`);
    return response.data; // Returns status 204 No Content
  },
};

export default devicesService;
