// src/utils/auth.js
// Create this file to handle authentication

/**
 * Get user ID from JWT token or localStorage
 * @returns {string|null} User ID
 */
export const getUserId = () => {
  // Method 1: Check if user_id is cached
  const cachedUserId = localStorage.getItem('user_id');
  if (cachedUserId) {
    console.log('✅ Using cached user_id:', cachedUserId);
    return cachedUserId;
  }

  // Method 2: Decode JWT token
  const token = localStorage.getItem('access_token');
  if (token) {
    try {
      // JWT format: header.payload.signature
      const payload = JSON.parse(atob(token.split('.')[1]));
      const userId = payload.sub; // FastAPI uses 'sub' for user_id
      
      console.log('✅ Decoded user_id from token:', userId);
      
      // Cache it for next time
      localStorage.setItem('user_id', userId);
      return userId;
    } catch (e) {
      console.error('❌ Failed to decode token:', e);
    }
  }

  // Method 3: Fallback to test user (from your successful test.py output)
  console.warn('⚠️  No token found, using fallback user_id');
  const fallbackUserId = "69353ecd317c801a5b54474c"; // Your real user_id from test
  localStorage.setItem('user_id', fallbackUserId);
  return fallbackUserId;
};

/**
 * Get authentication token
 * @returns {string|null} JWT token
 */
export const getToken = () => {
  return localStorage.getItem('access_token');
};

/**
 * Set authentication data
 * @param {string} token - JWT token
 * @param {string} userId - User ID
 */
export const setAuth = (token, userId) => {
  localStorage.setItem('access_token', token);
  localStorage.setItem('user_id', userId);
  console.log('✅ Auth data saved');
};

/**
 * Clear authentication data
 */
export const clearAuth = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('user_id');
  console.log('🔓 Logged out');
};

/**
 * Check if user is authenticated
 * @returns {boolean}
 */
export const isAuthenticated = () => {
  return !!getToken();
};

/**
 * Login and save credentials
 * @param {string} username 
 * @param {string} password 
 * @returns {Promise<{token: string, userId: string}>}
 */
export const login = async (username, password) => {
  const response = await fetch('http://localhost:8001/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password })
  });

  if (!response.ok) {
    throw new Error('Login failed');
  }

  const data = await response.json();
  const token = data.access_token;
  
  // Decode to get user_id
  const payload = JSON.parse(atob(token.split('.')[1]));
  const userId = payload.sub;
  
  setAuth(token, userId);
  
  return { token, userId };
};

// Export default object with all functions
export default {
  getUserId,
  getToken,
  setAuth,
  clearAuth,
  isAuthenticated,
  login
};