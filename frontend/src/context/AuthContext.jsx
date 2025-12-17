import React, { createContext, useContext, useState, useEffect } from 'react';
import {
    loginAPI,
    registerAPI,
    forgotPasswordAPI,
    resetPasswordAPI,
    googleLoginAPI
} from '../services/authService';
import { syncHistory } from '../services/api';

// Create context
const AuthContext = createContext(null);

// Token storage keys
const TOKEN_KEY = 'auth_token';
const USER_KEY = 'auth_user';
const REMEMBER_KEY = 'auth_remember';

// Helper functions for storage
const getStoredToken = () => {
    return localStorage.getItem(TOKEN_KEY) || sessionStorage.getItem(TOKEN_KEY);
};

const getStoredUser = () => {
    const userStr = localStorage.getItem(USER_KEY) || sessionStorage.getItem(USER_KEY);
    return userStr ? JSON.parse(userStr) : null;
};

const clearStorage = () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    localStorage.removeItem(REMEMBER_KEY);
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(USER_KEY);
};

// Auth Provider Component
export const AuthProvider = ({ children }) => {
    const [user, setUser] = useState(null);
    const [token, setToken] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    // Initialize auth state from storage on mount
    useEffect(() => {
        const storedToken = getStoredToken();
        const storedUser = getStoredUser();

        if (storedToken && storedUser) {
            setToken(storedToken);
            setUser(storedUser);
        }
        setLoading(false);
    }, []);

    // Save to storage helper
    const saveToStorage = (tokenData, userData, remember = true) => {
        // OAuth always uses localStorage (remember = true)
        const storage = remember ? localStorage : sessionStorage;
        storage.setItem(TOKEN_KEY, tokenData);
        storage.setItem(USER_KEY, JSON.stringify(userData));
        if (remember) {
            localStorage.setItem(REMEMBER_KEY, 'true');
        }
    };

    // Temp ID key for visual search history
    const TEMP_ID_KEY = 'visual_search_temp_id';

    // Sync temp detection history from guest session to user account
    const syncTempHistoryIfExists = async () => {
        const tempId = localStorage.getItem(TEMP_ID_KEY);
        if (tempId) {
            try {
                await syncHistory(tempId);
                localStorage.removeItem(TEMP_ID_KEY); // Clear temp_id after successful sync
                console.log('✅ Synced temp detection history');
            } catch (err) {
                console.warn('Could not sync temp history:', err);
            }
        }
    };

    // Process OAuth response (shared logic for Google/Facebook)
    const processOAuthResponse = async (response) => {
        const { access_token, username: userName, user_id, full_name, auth_provider } = response;

        const userData = {
            id: user_id,
            user_id: user_id, // For API compatibility
            username: userName,
            fullName: full_name,
            authProvider: auth_provider
        };

        setToken(access_token);
        setUser(userData);
        saveToStorage(access_token, userData, true); // Always remember OAuth logins

        // Sync temp detection history from guest session
        await syncTempHistoryIfExists();

        return { success: true };
    };

    // Login function (local)
    const login = async (username, password, remember = false) => {
        setError(null);
        setLoading(true);

        try {
            const response = await loginAPI(username, password);
            const { access_token, username: userName, user_id, full_name, auth_provider } = response;

            const userData = {
                id: user_id,
                user_id: user_id, // For API compatibility
                username: userName,
                fullName: full_name,
                authProvider: auth_provider
            };

            setToken(access_token);
            setUser(userData);
            saveToStorage(access_token, userData, remember);

            // Sync temp detection history from guest session
            await syncTempHistoryIfExists();

            return { success: true };
        } catch (err) {
            const message = err.message || 'Đăng nhập thất bại';
            setError(message);
            return { success: false, error: message };
        } finally {
            setLoading(false);
        }
    };

    // Google Login function
    const loginWithGoogle = async (googleCredential) => {
        setError(null);
        setLoading(true);

        try {
            const response = await googleLoginAPI(googleCredential);
            return processOAuthResponse(response);
        } catch (err) {
            const message = err.message || 'Đăng nhập Google thất bại';
            setError(message);
            return { success: false, error: message };
        } finally {
            setLoading(false);
        }
    };

    // Register function
    const register = async (username, password, email) => {
        setError(null);
        setLoading(true);

        try {
            await registerAPI(username, password, email);
            return { success: true, message: 'Đăng ký thành công! Vui lòng đăng nhập.' };
        } catch (err) {
            const message = err.message || 'Đăng ký thất bại';
            setError(message);
            return { success: false, error: message };
        } finally {
            setLoading(false);
        }
    };

    // Forgot password function
    const forgotPassword = async (username, email) => {
        setError(null);
        setLoading(true);

        try {
            const response = await forgotPasswordAPI(username, email);
            return { success: true, message: response.message };
        } catch (err) {
            const message = err.message || 'Không thể gửi email khôi phục';
            setError(message);
            return { success: false, error: message };
        } finally {
            setLoading(false);
        }
    };

    // Reset password function
    const resetPassword = async (resetToken, newPassword, confirmPassword) => {
        setError(null);
        setLoading(true);

        try {
            const response = await resetPasswordAPI(resetToken, newPassword, confirmPassword);
            return { success: true, message: response.message };
        } catch (err) {
            const message = err.message || 'Không thể đặt lại mật khẩu';
            setError(message);
            return { success: false, error: message };
        } finally {
            setLoading(false);
        }
    };

    // Logout function
    const logout = () => {
        setUser(null);
        setToken(null);
        setError(null);
        clearStorage();
    };

    // Clear error
    const clearError = () => {
        setError(null);
    };

    // Context value
    const value = {
        user,
        token,
        loading,
        error,
        isAuthenticated: !!token && !!user,
        login,
        loginWithGoogle,
        register,
        logout,
        forgotPassword,
        resetPassword,
        clearError
    };

    return (
        <AuthContext.Provider value={value}>
            {children}
        </AuthContext.Provider>
    );
};

// Custom hook for using auth context
export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
};

export default AuthContext;
