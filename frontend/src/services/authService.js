/**
 * Auth Service for Smart Sightseeing Support System
 * Handles all authentication API calls
 */

import axios from 'axios';

// Auth API URL - Use production URL or fallback to local proxy
const AUTH_API_URL = import.meta.env.VITE_AUTH_API_URL || '/auth';

// Create axios instance for auth endpoints
const authAPI = axios.create({
    baseURL: AUTH_API_URL,
    timeout: 15000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Response interceptor for error handling
authAPI.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('Auth API Error:', error);

        if (error.response) {
            // Server responded with error status
            const message = error.response.data?.detail || 'Đã xảy ra lỗi từ server';
            throw new Error(message);
        } else if (error.request) {
            // Request made but no response
            throw new Error('Không thể kết nối với server. Vui lòng kiểm tra backend Auth.');
        } else {
            // Something else happened
            throw new Error('Đã xảy ra lỗi: ' + error.message);
        }
    }
);

// ==========================================
// AUTH API FUNCTIONS
// ==========================================

/**
 * Login with username and password
 * @param {string} username 
 * @param {string} password 
 * @returns {Promise} Token and user info
 */
export const loginAPI = async (username, password) => {
    const response = await authAPI.post('/login', {
        username,
        password
    });
    return response.data;
};

/**
 * Register new account
 * @param {string} username 
 * @param {string} password 
 * @param {string} email 
 * @returns {Promise} Success message
 */
export const registerAPI = async (username, password, email) => {
    const response = await authAPI.post('/register', {
        username,
        password,
        email
    });
    return response.data;
};

/**
 * Request password reset email
 * @param {string} username 
 * @param {string} email 
 * @returns {Promise} Success message
 */
export const forgotPasswordAPI = async (username, email) => {
    const response = await authAPI.post('/forgot-password', {
        username,
        email
    });
    return response.data;
};

/**
 * Reset password with token from email
 * @param {string} token - Reset token from email link
 * @param {string} newPassword 
 * @param {string} confirmPassword 
 * @returns {Promise} Success message
 */
export const resetPasswordAPI = async (token, newPassword, confirmPassword) => {
    const response = await authAPI.post('/reset-password', {
        token,
        new_password: newPassword,
        confirm_password: confirmPassword
    });
    return response.data;
};

/**
 * Login with Google OAuth token
 * @param {string} googleToken - ID token from Google
 * @returns {Promise} Token and user info
 */
export const googleLoginAPI = async (googleToken) => {
    const response = await authAPI.post('/google', {
        token: googleToken
    });
    return response.data;
};

export default authAPI;
