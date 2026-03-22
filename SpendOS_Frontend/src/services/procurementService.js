import api from './api';

export const procurementService = {
  async analyze(requirements) {
    const response = await api.post('/procurement/analyze', requirements);
    return response.data;
  },
  
  async getAnalysisStatus(taskId) {
    const response = await api.get(`/procurement/status/${taskId}`);
    return response.data;
  },

  async getHistory() {
    const response = await api.get('/procurement/history');
    return response.data;
  },

  async deleteSession(sessionId) {
    const response = await api.delete(`/procurement/history/${sessionId}`);
    return response.data;
  }
};
