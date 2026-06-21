/**
 * services/ml.js
 * ==============
 * AI/ML Analytics API Client Service
 */

import api from './api';

export const mlService = {
  /**
   * Fetches overall device predictions, health metrics, and risk levels.
   */
  async getPredictions() {
    const response = await api.get('/ml/predictions');
    return response.data; // Returns List[DevicePredictionSummary]
  },

  /**
   * Fetches capacity forecasts and detailed anomaly trails for a specific device.
   * 
   * @param {string} deviceId - Device UUID
   */
  async getPredictionDetails(deviceId) {
    const response = await api.get(`/ml/predictions/${deviceId}`);
    return response.data; // Returns DevicePredictionDetails
  },

  /**
   * Triggers manual model retraining of Isolation Forest & Random Forest models.
   */
  async retrainModels() {
    const response = await api.post('/ml/retrain');
    return response.data; // Returns MLRetrainResponse
  },
};

export default mlService;
