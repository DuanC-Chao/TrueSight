import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: 'http://localhost:5001/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  }
});

// 请求拦截器
api.interceptors.request.use(
  config => {
    // 可以在这里添加认证信息等
    return config;
  },
  error => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  response => {
    return response.data;
  },
  error => {
    // 统一处理错误
    let errorMessage = '请求失败';
    if (error.response) {
      // 服务器返回错误
      const { status, data } = error.response;
      if (data && data.error) {
        errorMessage = data.error;
      } else {
        switch (status) {
          case 400:
            errorMessage = '请求参数错误';
            break;
          case 401:
            errorMessage = '未授权，请重新登录';
            break;
          case 403:
            errorMessage = '拒绝访问';
            break;
          case 404:
            errorMessage = '请求的资源不存在';
            break;
          case 500:
            errorMessage = '服务器内部错误';
            break;
          default:
            errorMessage = `请求失败(${status})`;
        }
      }
    } else if (error.request) {
      // 请求发出但没有收到响应
      errorMessage = '服务器无响应';
    }
    
    console.error('API请求错误:', errorMessage);
    return Promise.reject({ error: errorMessage });
  }
);

// API函数

// 健康检查
export const checkHealth = () => {
  return api.get('/health');
};

// 配置相关
export const getConfig = () => {
  return api.get('/config');
};

export const updateConfig = (config) => {
  return api.put('/config', config);
};

// 爬虫相关
export const startCrawl = (data) => {
  return api.post('/crawler/start', data);
};

export const getCrawlStatus = (taskId) => {
  return api.get(`/crawler/status/${taskId}`);
};

// 预处理相关
export const calculateTokens = (data) => {
  return api.post('/processor/token/calculate', data);
};

export const generateSummary = (data) => {
  return api.post('/processor/summary/generate', data);
};

export const generateQA = (data) => {
  return api.post('/processor/qa/generate', data);
};

export const getProcessStatus = (taskId) => {
  return api.get(`/processor/status/${taskId}`);
};

// 信息库相关
export const listRepositories = () => {
  return api.get('/repository/list');
};

export const createRepository = (data, isFormData = false) => {
  if (isFormData) {
    return api.post('/repository/create', data, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    });
  }
  return api.post('/repository/create', data);
};

export const getRepository = (name) => {
  return api.get(`/repository/${name}`);
};

export const updateRepository = (name, data) => {
  return api.put(`/repository/${name}`, data);
};

export const deleteRepository = (name) => {
  return api.delete(`/repository/${name}`);
};

export const getRepositoryFiles = (name, params = {}) => {
  return api.get(`/repository/${name}/files`, { params });
};

export const getRepositorySummaryFiles = (name) => {
  return api.get(`/repository/${name}/summary_files`);
};

export const getRepositoryQAFiles = (name) => {
  return api.get(`/repository/${name}/qa_files`);
};

export const getRepositoryFile = (name, path) => {
  return api.get(`/repository/${name}/file`, { params: { path } });
};

export const uploadFiles = (name, formData) => {
  return api.post(`/repository/${name}/upload`, formData, {
    headers: {
      'Content-Type': 'multipart/form-data'
    }
  });
};

export const uploadUrlFile = (name, data) => {
  return api.post(`/repository/${name}/upload_url`, data);
};

export const updateRepositoryStatus = (name, status) => {
  return api.put(`/repository/${name}/status`, { status });
};

export const setAutoUpdate = (name, data) => {
  return api.put(`/repository/${name}/auto_update`, data);
};

export const setDirectImport = (name, data) => {
  return api.put(`/repository/${name}/direct_import`, data);
};

export const batchUpdateRepositories = (data) => {
  return api.post('/repository/batch/update', data);
};

export const batchSetAutoUpdate = (data) => {
  return api.post('/repository/batch/auto_update', data);
};

export const batchSetDirectImport = (data) => {
  return api.post('/repository/batch/direct_import', data);
};

// RAGFlow 相关
export const listRAGFlowDatasets = (params = {}) => {
  return api.get('/ragflow/datasets', { params });
};

export const importRepositoryToRAGFlow = (name) => {
  return api.post(`/ragflow/import/${name}`);
};

export const updateRepositoryInRAGFlow = (name) => {
  return api.post(`/ragflow/update/${name}`);
};

export const deleteRepositoryFromRAGFlow = (name) => {
  return api.post(`/ragflow/delete/${name}`);
};

export const syncRepositoryWithRAGFlow = (name) => {
  return api.post(`/ragflow/sync/${name}`);
};

export const batchImportRepositoriesToRAGFlow = (data) => {
  return api.post('/ragflow/batch/import', data);
};

export const batchSyncRepositoriesWithRAGFlow = (data) => {
  return api.post('/ragflow/batch/sync', data);
};

// 调度相关
export const addAutoUpdateTask = (name) => {
  return api.post(`/scheduler/auto_update/${name}`);
};

// 错误日志相关
export const getErrorLogs = (params = {}) => {
  return api.get('/error_logs', { params });
};

export const clearErrorLog = (logId) => {
  return api.delete(`/error_logs/${logId}`);
};

export default api;
