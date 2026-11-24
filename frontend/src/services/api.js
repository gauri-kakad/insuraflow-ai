import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 60000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('insuraflow_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !window.location.pathname.includes('/login')) {
      localStorage.removeItem('insuraflow_token');
      localStorage.removeItem('insuraflow_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authService = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  getMe: () => api.get('/auth/me'),
};

export const claimsService = {
  list: (params = {}) => api.get('/claims', { params }),
  getById: (claimId) => api.get(`/claims/${claimId}`),
  create: (formData) =>
    api.post('/claims', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  delete: (claimId) => api.delete(`/claims/${claimId}`),
  process: (claimId, useDemoMode = null) =>
    api.post(`/claims/${claimId}/process`, { use_demo_mode: useDemoMode }),
  getStatus: (claimId) => api.get(`/claims/${claimId}/status`),
  getAssessment: (claimId) => api.get(`/claims/${claimId}/assessment`),
  submitReview: (claimId, payload) => api.post(`/claims/${claimId}/review`, payload),
  getAudit: (claimId) => api.get(`/claims/${claimId}/audit`),
  downloadReport: async (claimId) => {
    const response = await api.get(`/claims/${claimId}/report`, {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([response.data], { type: 'application/pdf' }));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', `InsuraFlow_Assessment_${claimId}.pdf`);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },
  getDashboardAnalytics: () => api.get('/analytics/dashboard'),
};

export default api;
