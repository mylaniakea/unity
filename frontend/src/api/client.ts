import axios from 'axios';

const api = axios.create({
    baseURL: '/api',
});

// Request interceptor - no auth needed for testing
api.interceptors.request.use(
    (config) => config,
    (error) => Promise.reject(error)
);

// Response interceptor - no redirect on 401
api.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('API Error:', error);
        return Promise.reject(error);
    }
);

export default api;
