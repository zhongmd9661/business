// API 基础配置
const API_BASE = window.location.origin;

// API 调用工具类
class ApiClient {
    constructor() {
        this.baseURL = API_BASE;
        this.token = localStorage.getItem('auth_token');
        this.user = JSON.parse(localStorage.getItem('user') || 'null');
    }

    async request(endpoint, options = {}) {
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers,
        };

        if (this.token && !options.skipAuth) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        const response = await fetch(`${this.baseURL}${endpoint}`, {
            ...options,
            headers,
        });

        if (response.status === 401) {
            this.logout();
            throw new Error('认证失败，请重新登录');
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `请求失败: ${response.status}`);
        }

        return data;
    }

    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    async post(endpoint, body) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(body),
        });
    }

    async put(endpoint, body) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(body),
        });
    }

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    async uploadFiles(files, onProgress) {
        const formData = new FormData();
        files.forEach(file => {
            formData.append('files', file);
        });

        const response = await fetch(`${this.baseURL}/api/tasks/upload`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.token}`,
            },
            body: formData,
        });

        if (response.status === 401) {
            this.logout();
            throw new Error('认证失败，请重新登录');
        }

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.detail || `上传失败: ${response.status}`);
        }

        return data;
    }

    setUser(user, token) {
        this.user = user;
        this.token = token;
        localStorage.setItem('user', JSON.stringify(user));
        localStorage.setItem('auth_token', token);
    }

    logout() {
        this.user = null;
        this.token = null;
        localStorage.removeItem('user');
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
    }

    isAuthenticated() {
        return !!this.token && !!this.user;
    }

    isAdmin() {
        return this.user?.role === 'admin';
    }
}

// 全局 API 客户端实例
const api = new ApiClient();
