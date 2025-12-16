/**
 * API Service for Smart Sightseeing Support System
 * Handles all API calls to the backend
 */

import axios from 'axios';

// API Base URLs - Use production URLs or fallback to local proxy
const BEFORE_API_URL = import.meta.env.VITE_BEFORE_API_URL || '/api';
const DURING_API_URL = import.meta.env.VITE_DURING_API_URL || '/during';

// Create axios instance for Before module (destinations, recommendations)
const api = axios.create({
    baseURL: BEFORE_API_URL,
    timeout: 30000,
    headers: {
        'Content-Type': 'application/json',
    },
});

// Response interceptor for error handling
api.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('API Error:', error);

        if (error.response) {
            // Server responded with error status
            const message = error.response.data?.detail || 'Đã xảy ra lỗi từ server';
            throw new Error(message);
        } else if (error.request) {
            // Request made but no response
            throw new Error('Không thể kết nối với server. Vui lòng kiểm tra backend.');
        } else {
            // Something else happened
            throw new Error('Đã xảy ra lỗi: ' + error.message);
        }
    }
);

// ==========================================
// API FUNCTIONS
// ==========================================

/**
 * Get paginated list of destinations with optional filters
 * @param {Object} filters - Hard constraint filters (all single strings)
 * @param {number} page - Page number (1-indexed)
 * @param {number} limit - Items per page
 * @param {string} sortBy - Sort option (matches backend SortOption enum)
 * @returns {Promise} Response with data, total, page info
 */
export const getDestinations = async (filters = {}, page = 1, limit = 12, sortBy = 'Đánh giá cao nhất') => {
    try {
        const params = new URLSearchParams({
            page: page.toString(),
            limit: limit.toString(),
            sort_by: sortBy,
        });

        // Add filters if they exist
        // All arrays: append each value separately for FastAPI to parse as List[str]
        if (filters.budget_range && Array.isArray(filters.budget_range)) {
            filters.budget_range.forEach(val => params.append('budget_range', val));
        }

        // Arrays: append each value separately for FastAPI to parse as List[str]
        if (filters.available_time && Array.isArray(filters.available_time)) {
            filters.available_time.forEach(val => params.append('available_time', val));
        }
        if (filters.companion_tag && Array.isArray(filters.companion_tag)) {
            filters.companion_tag.forEach(val => params.append('companion_tag', val));
        }
        if (filters.season_tag && Array.isArray(filters.season_tag)) {
            filters.season_tag.forEach(val => params.append('season_tag', val));
        }

        // Province: single string
        if (filters.location_province) {
            params.append('location_province', filters.location_province);
        }


        const response = await api.get(`/destinations?${params.toString()}`);
        return response.data;
    } catch (error) {
        throw error;
    }
};

/**
 * Get detailed information about a specific destination
 * @param {string} landmarkId - Unique ID of the destination
 * @returns {Promise} Destination details with weather info
 */
export const getDestinationDetail = async (landmarkId) => {
    try {
        const response = await api.get(`/destinations/${landmarkId}`);
        return response.data;
    } catch (error) {
        throw error;
    }
};

/**
 * Get AI-powered recommendations based on user's vibe prompt
 * @param {string} vibePrompt - User's preference description
 * @returns {Promise} AI-generated recommendations with justifications
 */
export const getRecommendations = async (vibePrompt) => {
    try {
        const response = await api.post('/recommendations', {
            vibe_prompt: vibePrompt,
        });
        return response.data;
    } catch (error) {
        throw error;
    }
};

/**
 * Perform semantic search using vector similarity (No LLM)
 * @param {string} query - Search query (vibe text)
 * @param {Object} filters - Optional hard constraint filters
 * @param {number} page - Page number (1-indexed)
 * @param {number} limit - Items per page
 * @param {string} sortBy - Sort option (matches backend SortOption enum)
 * @returns {Promise} Search results
 */
export const semanticSearch = async (query, filters = {}, page = 1, limit = 24, sortBy = 'Đánh giá cao nhất') => {
    try {
        // Build hard_constraints object from filters
        const hard_constraints = {};
        if (filters.budget_range) hard_constraints.budget_range = filters.budget_range;
        if (filters.available_time) hard_constraints.available_time = filters.available_time;
        if (filters.companion_tag) hard_constraints.companion_tag = filters.companion_tag;
        if (filters.season_tag) hard_constraints.season_tag = filters.season_tag;
        if (filters.location_province) hard_constraints.location_province = filters.location_province;

        // Include page, limit, and sort_by as query params
        const response = await api.post(`/search?page=${page}&limit=${limit}&sort_by=${encodeURIComponent(sortBy)}`, {
            query: query,
            hard_constraints: Object.keys(hard_constraints).length > 0 ? hard_constraints : null
        });
        return response.data;
    } catch (error) {
        throw error;
    }
};

/**
 * Visual search - upload image to recognize landmark
 * @param {File} imageFile - Image file to search
 * @param {string} tempId - Optional temp ID for guest users
 * @returns {Promise} Recognition result with landmark info
 */
export const visualSearch = async (imageFile, tempId = null) => {
    try {
        const formData = new FormData();
        formData.append('file', imageFile);

        const headers = { 'Content-Type': 'multipart/form-data' };

        // Add temp_id header for guest users
        if (tempId) {
            headers['X-Temp-ID'] = tempId;
        }

        // Add auth token if logged in
        const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }

        const response = await axios.post(`${DURING_API_URL}/visual-search`, formData, {
            headers,
            timeout: 60000,
        });
        return response.data;
    } catch (error) {
        console.error('Visual Search Error:', error);
        if (error.response) {
            throw new Error(error.response.data?.detail || 'Không thể nhận diện địa điểm');
        } else if (error.request) {
            throw new Error('Không thể kết nối với server Visual Search');
        } else {
            throw new Error('Đã xảy ra lỗi: ' + error.message);
        }
    }
};

/**
 * Sync temporary history to user's permanent history (During module)
 * @param {string} tempId - Temporary ID to sync
 * @returns {Promise} Sync result
 */
export const syncHistory = async (tempId) => {
    try {
        const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
        const response = await axios.post(
            `${DURING_API_URL}/history/sync`,
            { temp_id: tempId },
            {
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`,
                },
            }
        );
        return response.data;
    } catch (error) {
        console.error('Sync History Error:', error);
        throw error;
    }
};

/**
 * Get detection history for a user (During module)
 * Uses /history/summary endpoint which returns list of detection records
 * @returns {Promise} Detection history array
 */
export const getDetectionHistory = async () => {
    try {
        const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
        const response = await axios.get(`${DURING_API_URL}/history/summary`, {
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        });
        // Backend returns array directly, wrap in object for consistency
        return { history: response.data };
    } catch (error) {
        console.error('Get History Error:', error);
        throw error;
    }
};

/**
 * Get temporary detection history for guest users (During module)
 * Uses /history/temp-summary endpoint - no auth required
 * @param {string} tempId - Temporary ID from localStorage
 * @returns {Promise} Detection history array
 */
export const getTempHistory = async (tempId) => {
    try {
        if (!tempId) return { history: [] };
        const response = await axios.get(`${DURING_API_URL}/history/temp-summary`, {
            params: { temp_id: tempId },
        });
        return { history: response.data };
    } catch (error) {
        console.error('Get Temp History Error:', error);
        return { history: [] }; // Return empty on error for guests
    }
};

/**
 * Get detailed history for a specific landmark (During module)
 * @param {string} landmarkId - Landmark ID
 * @returns {Promise} History detail with landmark info
 */
export const getHistoryDetail = async (landmarkId) => {
    try {
        const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
        const response = await axios.get(`${DURING_API_URL}/history/detail/${landmarkId}`, {
            headers: {
                'Authorization': `Bearer ${token}`,
            },
        });
        return response.data;
    } catch (error) {
        console.error('Get History Detail Error:', error);
        throw error;
    }
};

/**
 * Delete history items (During module)
 * @param {string[]} imageUrls - Array of image URLs to delete
 * @returns {Promise} Delete result
 */
export const deleteHistory = async (imageUrls) => {
    try {
        const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
        const response = await axios.delete(`${DURING_API_URL}/history/delete`, {
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`,
            },
            data: { image_urls: imageUrls },
        });
        return response.data;
    } catch (error) {
        console.error('Delete History Error:', error);
        throw error;
    }
};

export default api;


