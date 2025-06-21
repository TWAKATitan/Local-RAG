import axios from 'axios';

// 創建axios實例，明確指定後端API地址
const api = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 3000000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// 請求攔截器
api.interceptors.request.use(
  (config) => {
    console.log('API Request:', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('Request Error:', error);
    return Promise.reject(error);
  }
);

// 響應攔截器
api.interceptors.response.use(
  (response) => {
    console.log('API Response:', response.status, response.config.url);
    return response;
  },
  (error) => {
    console.error('Response Error:', error.response?.status, error.config?.url, error.message);
    return Promise.reject(error);
  }
);

// 基礎API常量 (保留以備將來使用)
// eslint-disable-next-line no-unused-vars
const API_BASE_URL = 'http://localhost:8000';

// 聊天記錄相關API
export const saveChatSession = async (messages) => {
  try {
    const response = await api.post('/chat/save-session', messages);
    return response.data;
  } catch (error) {
    console.error('Error saving chat session:', error);
    throw error;
  }
};

export const loadCurrentChatSession = async () => {
  try {
    const response = await api.get('/chat/load-session');
    return response.data;
  } catch (error) {
    console.error('Error loading current chat session:', error);
    throw error;
  }
};

export const getChatSessions = async () => {
  try {
    const response = await api.get('/chat/sessions');
    return response.data;
  } catch (error) {
    console.error('Error getting chat sessions:', error);
    throw error;
  }
};

export const getChatSession = async (sessionId) => {
  try {
    const response = await api.get(`/chat/sessions/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error getting chat session:', error);
    throw error;
  }
};

export const setCurrentChatSession = async (sessionId) => {
  try {
    const response = await api.post(`/chat/sessions/${sessionId}/set-current`);
    return response.data;
  } catch (error) {
    console.error('Error setting current chat session:', error);
    throw error;
  }
};

export const deleteChatSession = async (sessionId) => {
  try {
    const response = await api.delete(`/chat/sessions/${sessionId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting chat session:', error);
    throw error;
  }
};

export const createNewChatSession = async () => {
  try {
    const response = await api.post('/chat/new-session');
    return response.data;
  } catch (error) {
    console.error('Error creating new chat session:', error);
    throw error;
  }
};

export const clearCurrentChatSession = async () => {
  try {
    const response = await api.delete('/chat/current-session');
    return response.data;
  } catch (error) {
    console.error('Error clearing current chat session:', error);
    throw error;
  }
};

// 改進的刪除文檔功能（支持強制刪除）
export const deleteDocument = async (filename, force = false) => {
  try {
    const params = force ? { force: true } : {};
    const response = await api.delete(`/documents/${filename}`, { params });
    return response.data;
  } catch (error) {
    console.error('Error deleting document:', error);
    throw error;
  }
};

// 批量刪除所有文檔（危險操作，僅供後端使用）
export const deleteAllDocuments = async () => {
  try {
    const response = await api.delete('/api/documents/delete-all');
    return response.data;
  } catch (error) {
    console.error('Error deleting all documents:', error);
    throw error;
  }
};

// 上傳狀態管理API
export const createUploadState = async () => {
  try {
    const response = await api.post('/api/upload-state/create');
    return response.data;
  } catch (error) {
    console.error('Error creating upload state:', error);
    throw error;
  }
};

export const getUploadState = async (stateId) => {
  try {
    const response = await api.get(`/api/upload-state/${stateId}`);
    return response.data;
  } catch (error) {
    console.error('Error getting upload state:', error);
    throw error;
  }
};

export const updateUploadState = async (stateId, files) => {
  try {
    const response = await api.put(`/api/upload-state/${stateId}`, files);
    return response.data;
  } catch (error) {
    console.error('Error updating upload state:', error);
    throw error;
  }
};

export const deleteUploadState = async (stateId) => {
  try {
    const response = await api.delete(`/api/upload-state/${stateId}`);
    return response.data;
  } catch (error) {
    console.error('Error deleting upload state:', error);
    throw error;
  }
};

export const debugUploadStates = async () => {
  try {
    const response = await api.get('/api/upload-state/debug');
    return response.data;
  } catch (error) {
    console.error('Error getting upload states debug info:', error);
    throw error;
  }
};

// 維護功能API
export const cleanupOrphanedData = async () => {
  try {
    const response = await api.post('/maintenance/cleanup-orphaned');
    return response.data;
  } catch (error) {
    console.error('Error cleaning up orphaned data:', error);
    throw error;
  }
};

export const checkDataConsistency = async () => {
  try {
    const response = await api.get('/maintenance/check-consistency');
    return response.data;
  } catch (error) {
    console.error('Error checking data consistency:', error);
    throw error;
  }
};

// 原有的API函數保持不變
export default api; 