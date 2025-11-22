import axios from 'axios';

// --- ĐOẠN QUAN TRỌNG NHẤT ---
// Logic: Ưu tiên lấy từ biến môi trường (lúc deploy), 
// nếu không có thì dùng localhost (lúc code trên máy).
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000'; 
// -----------------------------

const axiosClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
});

export default axiosClient;