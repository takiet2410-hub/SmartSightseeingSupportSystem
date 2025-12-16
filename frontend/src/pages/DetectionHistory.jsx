import { useState, useEffect } from 'react';
import { getDetectionHistory, syncHistory, deleteHistory } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { useNavigate, Link } from 'react-router-dom';
import ShareButtons from '../components/ShareButtons';
import './DetectionHistory.css';

const DetectionHistory = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [syncing, setSyncing] = useState(false);
    const [syncMessage, setSyncMessage] = useState(null);
    const [selectMode, setSelectMode] = useState(false);
    const [selected, setSelected] = useState([]);
    const [deleting, setDeleting] = useState(false);

    useEffect(() => {
        if (user) {
            // Auto-sync temp history on login
            handleAutoSync();
            fetchHistory();
        }
    }, [user]);

    // Auto sync temp history when user logs in
    const handleAutoSync = async () => {
        const tempId = localStorage.getItem('detection_temp_id');
        if (tempId) {
            try {
                setSyncing(true);
                const result = await syncHistory(tempId);
                if (result.status === 'synced' && result.count > 0) {
                    setSyncMessage(`✅ Đã đồng bộ ${result.count} mục từ lịch sử tạm`);
                    localStorage.removeItem('detection_temp_id');
                    setTimeout(() => setSyncMessage(null), 3000);
                }
            } catch (err) {
                console.error('Sync error:', err);
            } finally {
                setSyncing(false);
            }
        }
    };

    const fetchHistory = async () => {
        try {
            setLoading(true);
            const data = await getDetectionHistory();
            setHistory(data.history || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    // Handle delete selected items
    const handleDelete = async () => {
        if (selected.length === 0) return;
        if (!confirm(`Xóa ${selected.length} mục đã chọn?`)) return;

        try {
            setDeleting(true);
            await deleteHistory(selected);
            // Remove from local state
            setHistory(prev => prev.filter(item => !selected.includes(item.user_image_url)));
            setSelected([]);
            setSelectMode(false);
        } catch (err) {
            alert('Lỗi: ' + err.message);
        } finally {
            setDeleting(false);
        }
    };

    const toggleSelect = (imageUrl) => {
        setSelected(prev =>
            prev.includes(imageUrl)
                ? prev.filter(url => url !== imageUrl)
                : [...prev, imageUrl]
        );
    };

    if (!user) {
        return (
            <div className="detection-history">
                <div className="auth-required">
                    <h2>🔒 Yêu cầu đăng nhập</h2>
                    <p>Bạn cần đăng nhập để xem lịch sử nhận diện.</p>
                    <button onClick={() => navigate('/login')} className="login-btn">
                        Đăng nhập ngay
                    </button>
                </div>
            </div>
        );
    }

    if (loading) {
        return (
            <div className="detection-history">
                <div className="loading">
                    <div className="spinner"></div>
                    <p>{syncing ? 'Đang đồng bộ...' : 'Đang tải lịch sử...'}</p>
                </div>
            </div>
        );
    }

    return (
        <div className="detection-history">
            <div className="page-header">
                <h1>Lịch sử nhận diện</h1>
                <div className="header-actions">
                    {history.length > 0 && (
                        <button
                            onClick={() => {
                                setSelectMode(!selectMode);
                                setSelected([]);
                            }}
                            className={`select-btn ${selectMode ? 'active' : ''}`}
                        >
                            {selectMode ? 'Hủy' : 'Chọn'}
                        </button>
                    )}
                    <button onClick={() => navigate('/visual-search')} className="search-btn">
                        + Nhận diện mới
                    </button>
                </div>
            </div>

            {syncMessage && <div className="sync-message">{syncMessage}</div>}
            {error && <div className="error-message">{error}</div>}

            {/* Delete bar */}
            {selectMode && (
                <div className="delete-bar">
                    <div className="delete-bar-left">
                        <span>Đã chọn {selected.length} / {history.length} mục</span>
                        <button
                            onClick={() => {
                                if (selected.length === history.length) {
                                    setSelected([]);
                                } else {
                                    setSelected(history.map(item => item.user_image_url));
                                }
                            }}
                            className="select-all-btn"
                        >
                            {selected.length === history.length ? 'Bỏ chọn tất cả' : 'Chọn tất cả'}
                        </button>
                    </div>
                    <button
                        onClick={handleDelete}
                        disabled={deleting || selected.length === 0}
                        className="delete-btn"
                    >
                        {deleting ? 'Đang xóa...' : `Xóa ${selected.length > 0 ? `(${selected.length})` : ''}`}
                    </button>
                </div>
            )}

            {history.length === 0 ? (
                <div className="empty-state">
                    <span className="empty-icon"></span>
                    <h3>Chưa có lịch sử nhận diện</h3>
                    <p>Hãy thử tính năng nhận diện địa điểm bằng hình ảnh!</p>
                    <button onClick={() => navigate('/visual-search')} className="search-btn large">
                        Nhận diện ngay
                    </button>
                </div>
            ) : (
                <div className="history-list">
                    {history.map((item, index) => (
                        <div
                            key={index}
                            className={`history-item ${selectMode ? 'selectable' : ''} ${selected.includes(item.user_image_url) ? 'selected' : ''}`}
                            onClick={() => selectMode && toggleSelect(item.user_image_url)}
                        >
                            {selectMode && (
                                <div className="checkbox">
                                    {selected.includes(item.user_image_url) ? '☑' : '☐'}
                                </div>
                            )}
                            <div className="item-image">
                                <img src={item.user_image_url} alt="Uploaded" />
                            </div>
                            <div className="item-info">
                                <h4>{item.name}</h4>
                                <div className="item-meta">
                                    <span className="score">
                                        🎯 {(item.similarity_score * 100).toFixed(1)}%
                                    </span>
                                    <span className="date">
                                        {new Date(item.timestamp).toLocaleString('vi-VN')}
                                    </span>
                                </div>
                            </div>
                            {!selectMode && (
                                <div className="item-actions">
                                    <ShareButtons
                                        title={`Khám phá ${item.name}`}
                                        text={`Tôi đã khám phá ${item.name} với Smart Sightseeing lúc ${new Date(item.timestamp).toLocaleString('vi-VN')} tại ${item.location_province || 'Việt Nam'}!`}
                                        url={`${window.location.origin}/destination/${item.landmark_id}`}
                                        ogUrl={`${window.location.origin}/api/og/${item.landmark_id}`}
                                        userImageUrl={item.user_image_url}
                                        timestamp={item.timestamp}
                                        compact={true}
                                    />
                                    <Link
                                        to={`/destination/${item.landmark_id}`}
                                        className="view-btn"
                                    >
                                        Xem chi tiết →
                                    </Link>
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            )}
        </div>
    );
};

export default DetectionHistory;

