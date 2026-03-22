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
  },

  getAnalysisEventSource(taskId) {
    const url = `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api"}/procurement/events/${taskId}`;
    return new EventSource(url, { withCredentials: true });
  },
  
  async exportResults(sessionId) {
    const response = await api.get(`/procurement/export/${sessionId}`, {
      responseType: 'blob'
    });
    
    // Create a temporary link element to trigger the download
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    
    // Extract filename from content-disposition header if possible
    const contentDisposition = response.headers['content-disposition'];
    let fileName = `procurement_results_${sessionId.substring(0, 8)}.csv`;
    if (contentDisposition) {
      const fileNameMatch = contentDisposition.match(/filename="?(.+)"?/);
      if (fileNameMatch && fileNameMatch.length > 1) {
        fileName = fileNameMatch[1];
      }
    }
    
    link.setAttribute('download', fileName);
    document.body.appendChild(link);
    link.click();
    
    // Cleanup
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
    
    return true;
  }
};
