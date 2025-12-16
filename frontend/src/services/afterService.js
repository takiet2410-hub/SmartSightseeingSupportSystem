/**
 * After Service API - Album Creation & Trip Summary
 * Backend: Port 8003
 */

import axios from 'axios';

const AFTER_API_URL = import.meta.env.VITE_AFTER_API_URL || '/after';

const afterApi = axios.create({
    baseURL: AFTER_API_URL,
    timeout: 1500000, // 25 minutes for large uploads
});

// Add auth token to requests
afterApi.interceptors.request.use((config) => {
    const token = localStorage.getItem('auth_token') || sessionStorage.getItem('auth_token');
    if (token) {
        config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
});

// Error handling
afterApi.interceptors.response.use(
    (response) => response,
    (error) => {
        console.error('After API Error:', error);
        if (error.response) {
            throw new Error(error.response.data?.detail || 'Đã xảy ra lỗi từ server');
        } else if (error.request) {
            throw new Error('Không thể kết nối với server. Vui lòng thử lại.');
        }
        throw new Error('Đã xảy ra lỗi: ' + error.message);
    }
);

/**
 * Create album from uploaded photos
 * @param {FileList|File[]} files - Array of image files
 * @param {function} onProgress - Progress callback (0-100)
 * @returns {Promise} Created albums
 */
export const createAlbum = async (files, onProgress = null) => {
    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }

    const response = await afterApi.post('/create-album', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
        onUploadProgress: (progressEvent) => {
            if (onProgress && progressEvent.total) {
                const percent = Math.round((progressEvent.loaded * 100) / progressEvent.total);
                onProgress(percent);
            }
        },
    });
    return response.data;
};

/**
 * Get user's albums
 * @returns {Promise} Array of albums
 */
export const getMyAlbums = async () => {
    const response = await afterApi.get('/my-albums');
    return response.data;
};

/**
 * Create trip summary from album data
 * @param {Object} albumData - Album data for summary
 * @param {Array} manualLocations - Optional manual locations (with album_id, lat, lon, name)
 * @returns {Promise} Trip summary response
 */
export const createTripSummary = async (albumData, manualLocations = []) => {
    const response = await afterApi.post('/summary/create', {
        album_data: albumData,
        manual_locations: manualLocations,
    });
    return response.data;
};

/**
 * Get summary history
 * @returns {Promise} Array of past summaries
 */
export const getSummaryHistory = async () => {
    const response = await afterApi.get('/summary/history');
    return response.data;
};

/**
 * Delete a trip summary
 * @param {string} summaryId - Summary ID to delete
 * @returns {Promise} Success message
 */
export const deleteTripSummary = async (summaryId) => {
    const response = await afterApi.delete(`/summary/${summaryId}`);
    return response.data;
};

/**
 * Geocode an address using OpenStreetMap via backend
 * @param {string} address - Address to search
 * @returns {Promise} Array of geocoding results [{lat, lon, display_name}]
 */
export const geocodeAddress = async (address) => {
    const response = await afterApi.post('/geocode/osm', {
        address: address,
    });
    return response.data;
};

/**
 * Connect to WebSocket for real-time updates
 * @param {string} userId - User ID
 * @param {function} onMessage - Message handler
 * @returns {WebSocket} WebSocket connection
 */
export const connectWebSocket = (userId, onMessage) => {
    const wsUrl = AFTER_API_URL.replace('http', 'ws').replace('https', 'wss');
    const ws = new WebSocket(`${wsUrl}/ws/${userId}`);

    ws.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            onMessage(data);
        } catch (e) {
            console.error('WebSocket parse error:', e);
        }
    };

    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };

    return ws;
};

// ==========================================
// ALBUM SHARING APIs
// ==========================================

/**
 * Create share link for an album
 * @param {string} albumId - Album ID
 * @returns {Promise} Share token and URL hint
 */
export const createShareLink = async (albumId) => {
    const response = await afterApi.post(`/albums/${albumId}/share`);
    return response.data;
};

/**
 * Revoke (disable) share link for an album
 * @param {string} albumId - Album ID
 * @returns {Promise} Success message
 */
export const revokeShareLink = async (albumId) => {
    const response = await afterApi.delete(`/albums/${albumId}/share`);
    return response.data;
};

/**
 * View shared album (NO AUTH REQUIRED)
 * @param {string} shareToken - Share token from URL
 * @returns {Promise} Album data (title, photos, cover, download URL)
 */
export const getSharedAlbum = async (shareToken) => {
    // Use axios directly without auth interceptor
    const response = await axios.get(`${AFTER_API_URL}/shared-albums/${shareToken}`);
    return response.data;
};

// ==========================================
// ALBUM MANAGEMENT APIs
// ==========================================

/**
 * Delete an album permanently
 * @param {string} albumId - Album ID
 * @returns {Promise} Success message
 */
export const deleteAlbum = async (albumId) => {
    const response = await afterApi.delete(`/albums/${albumId}`);
    return response.data;
};

/**
 * Rename an album
 * @param {string} albumId - Album ID
 * @param {string} newTitle - New album title
 * @returns {Promise} Success message
 */
export const renameAlbum = async (albumId, newTitle) => {
    const response = await afterApi.patch(`/albums/${albumId}/rename`, {
        title: newTitle
    });
    return response.data;
};

/**
 * Delete a photo from an album
 * @param {string} albumId - Album ID
 * @param {string} photoId - Photo ID
 * @returns {Promise} Success message
 */
export const deletePhotoFromAlbum = async (albumId, photoId) => {
    const response = await afterApi.delete(`/albums/${albumId}/photos/${photoId}`);
    return response.data;
};

export default afterApi;

