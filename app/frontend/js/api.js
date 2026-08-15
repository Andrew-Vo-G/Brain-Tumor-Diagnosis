const API_BASE_URL = (() => {
    // If frontend is served by the backend itself, keep relative path.
    if (window.location.origin.includes("127.0.0.1:8000") || window.location.origin.includes("localhost:8000")) {
        return "/api";
    }
    // Fallback for cases where frontend is opened from another origin (Live Server/file://).
    return "http://127.0.0.1:8000/api";
})();
const API = {
    getHomePage(role) {
        return role === "doctor" ? "doctor-dashboard.html" : "patient.html";
    },
    _buildUrl(path, query = {}) {
        const base = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
        const origin = window.location.origin === "null" ? "http://127.0.0.1:8000" : window.location.origin;
        const url = new URL(`${base}${path}`, origin);
        Object.entries(query).forEach(([k, v]) => {
            if (v !== null && v !== undefined && v !== "") {
                url.searchParams.set(k, String(v));
            }
        });
        return url.toString();
    },
    getUploadUrl(imagePath) {
        if (!imagePath) return '';
        const base = API_BASE_URL.replace('/api', '/uploads');
        return `${base}/${imagePath}`;
    },
    async register(username, password, fullName, role = 'patient') {
        const response = await fetch(`${API_BASE_URL}/auth/register`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, full_name: fullName, role })
        });
        if (!response.ok) throw new Error((await response.json()).detail || 'Registration failed');
        return response.json();
    },

    async login(username, password) {
        const formData = new URLSearchParams();
        formData.append('username', username);
        formData.append('password', password);

        let response;
        try {
            response = await fetch(`${API_BASE_URL}/auth/token`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
                body: formData
            });
        } catch (error) {
            throw new Error('Cannot connect to the server. Please make sure the web app is running.');
        }

        if (!response.ok) {
            let detail = 'Invalid credentials';
            try {
                const err = await response.json();
                if (err?.detail) {
                    detail = err.detail;
                }
            } catch (_) {}
            throw new Error(detail);
        }
        const data = await response.json();
        
        localStorage.setItem('token', data.access_token);
        localStorage.setItem('user', JSON.stringify(data.user));
        return data.user;
    },

    logout() {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        window.location.href = 'login.html';
    },

    getToken() {
        return localStorage.getItem('token');
    },

    getUser() {
        const user = localStorage.getItem('user');
        return user ? JSON.parse(user) : null;
    },

    async getMe() {
        const response = await fetch(`${API_BASE_URL}/users/me`, {
            headers: { 'Authorization': `Bearer ${this.getToken()}` }
        });
        if (response.status === 401) this.logout();
        const user = await response.json();
        localStorage.setItem('user', JSON.stringify(user));
        return user;
    },

    async updateProfile(height, weight) {
        const response = await fetch(`${API_BASE_URL}/users/profile`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getToken()}` 
            },
            body: JSON.stringify({ height: parseFloat(height) || 0, weight: parseFloat(weight) || 0 })
        });
        if (!response.ok) throw new Error('Failed to update profile');
        const user = await response.json();
        localStorage.setItem('user', JSON.stringify(user));
        return user;
    },

    async changePassword(newPassword) {
        const response = await fetch(`${API_BASE_URL}/users/password`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getToken()}` 
            },
            body: JSON.stringify({ new_password: newPassword })
        });
        if (!response.ok) throw new Error((await response.json()).detail || 'Failed to change password');
        return await response.json();
    },

    async getPatients() {
        const response = await fetch(`${API_BASE_URL}/users/patients`, {
            headers: { 'Authorization': `Bearer ${this.getToken()}` }
        });
        if (!response.ok) throw new Error('Failed to fetch patients');
        return await response.json();
    },

    async updatePatientProfile(userId, height, weight) {
        const response = await fetch(`${API_BASE_URL}/users/${userId}/profile`, {
            method: 'PUT',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getToken()}` 
            },
            body: JSON.stringify({ height: parseFloat(height) || 0, weight: parseFloat(weight) || 0 })
        });
        if (!response.ok) throw new Error('Failed to update patient profile');
        return await response.json();
    },

    async getRecords(patientId = null) {
        const response = await fetch(this._buildUrl('/records', { patient_id: patientId }), {
            headers: { 'Authorization': `Bearer ${this.getToken()}` }
        });
        if (response.status === 401) {
            this.logout();
        }
        if (!response.ok) {
            let detail = 'Failed to load records';
            try {
                const err = await response.json();
                if (err && err.detail) detail = err.detail;
            } catch (_) {}
            throw new Error(detail);
        }
        const data = await response.json();
        return Array.isArray(data) ? data : [];
    },

    async updateRecord(recordId, data) {
        const response = await fetch(`${API_BASE_URL}/records/${recordId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getToken()}`
            },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error((await response.json()).detail || 'Failed to update record');
        return await response.json();
    },

    async deleteRecord(recordId) {
        const response = await fetch(`${API_BASE_URL}/records/${recordId}`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${this.getToken()}` }
        });
        if (!response.ok) throw new Error('Failed to delete record');
        return await response.json();
    },

    async predict(imageFile, patientId, notes = '', modelChoice = 'ensemble') {
        const formData = new FormData();
        formData.append('file', imageFile);
        formData.append('patient_id', patientId);
        if (notes) formData.append('notes', notes);
        formData.append('model_choice', modelChoice);

        const response = await fetch(`${API_BASE_URL}/predict`, {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${this.getToken()}` },
            body: formData
        });
        
        if (!response.ok) {
            let detail = 'Prediction failed';
            try {
                const errData = await response.json();
                if (errData.detail) detail = errData.detail;
            } catch(e) {}
            throw new Error(detail);
        }
        return response.json();
    },

    // --- CHAT API ---
    async getChatContacts() {
        const response = await fetch(`${API_BASE_URL}/messages/contacts`, {
            headers: { 'Authorization': `Bearer ${this.getToken()}` }
        });
        if (!response.ok) throw new Error('Failed to load contacts');
        return await response.json();
    },

    async getMessages(otherUserId) {
        const response = await fetch(`${API_BASE_URL}/messages/${otherUserId}`, {
            headers: { 'Authorization': `Bearer ${this.getToken()}` }
        });
        if (!response.ok) {
            let detail = 'Failed to load messages';
            try {
                const err = await response.json();
                if (err && err.detail) detail = err.detail;
            } catch (_) {}
            throw new Error(detail);
        }
        return await response.json();
    },

    async sendMessage(receiverId, content) {
        const response = await fetch(`${API_BASE_URL}/messages`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getToken()}`
            },
            body: JSON.stringify({ receiver_id: receiverId, content })
        });
        if (!response.ok) {
            let detail = 'Failed to send message';
            try {
                const err = await response.json();
                if (err && err.detail) detail = err.detail;
            } catch (_) {}
            throw new Error(detail);
        }
        return await response.json();
    },

    async logSymptom(symptomName, severity, notes = '') {
        const response = await fetch(`${API_BASE_URL}/symptoms`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getToken()}`
            },
            body: JSON.stringify({ symptom_name: symptomName, severity: parseInt(severity), notes })
        });
        if (!response.ok) {
            let detail = 'Failed to log symptom';
            try {
                const err = await response.json();
                if (err && err.detail) detail = err.detail;
            } catch (_) {}
            throw new Error(detail);
        }
        return await response.json();
    },

    async getSymptoms() {
        const response = await fetch(`${API_BASE_URL}/symptoms`, {
            headers: { 'Authorization': `Bearer ${this.getToken()}` }
        });
        if (!response.ok) {
            let detail = 'Failed to load symptoms';
            try {
                const err = await response.json();
                if (err && err.detail) detail = err.detail;
            } catch (_) {}
            throw new Error(detail);
        }
        return await response.json();
    },

    async bookAppointment(doctorId, date, notes = '') {
        const response = await fetch(`${API_BASE_URL}/appointments`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${this.getToken()}`
            },
            body: JSON.stringify({ doctor_id: doctorId, appointment_date: date, notes })
        });
        if (!response.ok) {
            let detail = 'Failed to book appointment';
            try {
                const err = await response.json();
                if (err && err.detail) detail = err.detail;
            } catch (_) {}
            throw new Error(detail);
        }
        return await response.json();
    },

    async getAppointments() {
        const response = await fetch(`${API_BASE_URL}/appointments`, {
            headers: { 'Authorization': `Bearer ${this.getToken()}` }
        });
        if (!response.ok) {
            let detail = 'Failed to load appointments';
            try {
                const err = await response.json();
                if (err && err.detail) detail = err.detail;
            } catch (_) {}
            throw new Error(detail);
        }
        return await response.json();
    },

    async getDoctors() {
        const response = await fetch(`${API_BASE_URL}/doctors`, {
            headers: { 'Authorization': `Bearer ${this.getToken()}` }
        });
        if (!response.ok) throw new Error('Failed to load doctors');
        return await response.json();
    },

    async warmup() {
        const response = await fetch(`${API_BASE_URL}/warmup`, {
            method: 'POST'
        });
        if (!response.ok) throw new Error('Warmup failed');
        return await response.json();
    },

    async health() {
        const response = await fetch(`${API_BASE_URL}/health`);
        if (!response.ok) throw new Error('Health check failed');
        return await response.json();
    }
};

// Check Auth state on load
function requireAuth() {
    if (!API.getToken()) {
        window.location.href = 'login.html';
    }
}

function redirectIfAuth() {
    const user = API.getUser();
    if (API.getToken() && user) {
        window.location.href = API.getHomePage(user.role);
    }
}
