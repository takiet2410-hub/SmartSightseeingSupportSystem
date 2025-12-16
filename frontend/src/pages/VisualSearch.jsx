import React, { useState, useRef } from 'react';
import { Link } from 'react-router-dom';
import { visualSearch } from '../services/api';
import { useAuth } from '../context/AuthContext';
import ShareButtons from '../components/ShareButtons';
import './VisualSearch.css';

const TEMP_ID_KEY = 'visual_search_temp_id';

const VisualSearch = () => {
    const { user } = useAuth();
    const [selectedFile, setSelectedFile] = useState(null);
    const [preview, setPreview] = useState(null);
    const [loading, setLoading] = useState(false);
    const [result, setResult] = useState(null);
    const [error, setError] = useState(null);
    const fileInputRef = useRef(null);

    // Get or create temp_id for guests
    const getTempId = () => {
        if (user) return null; // Don't use temp_id if logged in
        let tempId = localStorage.getItem(TEMP_ID_KEY);
        return tempId;
    };

    const handleFileSelect = (e) => {
        const file = e.target.files?.[0];
        if (file) {
            if (!file.type.startsWith('image/')) {
                setError('Vui lòng chọn file hình ảnh');
                return;
            }
            setSelectedFile(file);
            setPreview(URL.createObjectURL(file));
            setResult(null);
            setError(null);
        }
    };

    const handleDrop = (e) => {
        e.preventDefault();
        const file = e.dataTransfer.files?.[0];
        if (file && file.type.startsWith('image/')) {
            setSelectedFile(file);
            setPreview(URL.createObjectURL(file));
            setResult(null);
            setError(null);
        }
    };

    const handleSearch = async () => {
        if (!selectedFile) return;

        setLoading(true);
        setError(null);
        setResult(null);

        try {
            const tempId = getTempId();
            const data = await visualSearch(selectedFile, tempId);

            // If backend returns a new temp_id, store it for future searches
            if (data.temp_id && !user) {
                localStorage.setItem(TEMP_ID_KEY, data.temp_id);
            }

            setResult(data);

            // Save successful result to localStorage for check-in history
            if (data.status === 'success' && data.landmark_id) {
                const historyItem = {
                    id: data.landmark_id,
                    landmark_id: data.landmark_id,
                    name: data.landmark_info?.name,
                    location_province: data.landmark_info?.location_province,
                    image_url: data.landmark_info?.image_urls?.[0],
                    similarity_score: data.similarity_score,
                    created_at: new Date().toISOString()
                };

                const existingHistory = JSON.parse(localStorage.getItem('checkin_history') || '[]');
                // Add to beginning, limit to 50 items
                const updatedHistory = [historyItem, ...existingHistory].slice(0, 50);
                localStorage.setItem('checkin_history', JSON.stringify(updatedHistory));
            }
        } catch (err) {
            setError(err.message || 'Không thể nhận diện địa điểm');
        } finally {
            setLoading(false);
        }
    };

    const resetSearch = () => {
        setSelectedFile(null);
        setPreview(null);
        setResult(null);
        setError(null);
        if (fileInputRef.current) {
            fileInputRef.current.value = '';
        }
    };

    return (
        <div className="visual-search-page">
            <div className="container">
                <div className="page-header">
                    <h1>Tìm kiếm bằng hình ảnh</h1>
                    <p>Upload ảnh địa điểm du lịch để AI nhận diện</p>
                </div>

                {/* Upload Area */}
                {!preview && (
                    <div
                        className="upload-area"
                        onClick={() => fileInputRef.current?.click()}
                        onDrop={handleDrop}
                        onDragOver={(e) => e.preventDefault()}
                    >
                        <div className="upload-icon"></div>
                        <p>Kéo thả ảnh vào đây hoặc click để chọn</p>
                        <span className="upload-hint">Hỗ trợ: JPG, PNG, WebP</span>
                        <input
                            ref={fileInputRef}
                            type="file"
                            accept="image/*"
                            onChange={handleFileSelect}
                            hidden
                        />
                    </div>
                )}

                {/* Preview */}
                {preview && (
                    <div className="preview-section">
                        <div className="preview-image">
                            <img src={preview} alt="Preview" />
                        </div>
                        <div className="preview-actions">
                            <button
                                className="btn btn-primary btn-lg"
                                onClick={handleSearch}
                                disabled={loading}
                            >
                                {loading ? (
                                    <>
                                        <span className="spinner"></span>
                                        Đang nhận diện...
                                    </>
                                ) : (
                                    'Tìm kiếm'
                                )}
                            </button>
                            <button
                                className="btn btn-secondary"
                                onClick={resetSearch}
                                disabled={loading}
                            >
                                Chọn ảnh khác
                            </button>
                        </div>
                    </div>
                )}

                {/* Error */}
                {error && (
                    <div className="error-msg">
                        {error}
                    </div>
                )}

                {/* Result Modal Overlay */}
                {result && (
                    <div className="result-overlay">
                        <div className="result-modal">
                            {result.status === 'success' ? (
                                <>
                                    {/* Large Confidence Box */}
                                    <div className="confidence-box">
                                        <span className="confidence-label">Độ chính xác</span>
                                        <span className="confidence-value">
                                            {(result.similarity_score * 100).toFixed(1)}%
                                        </span>
                                        <span className="confidence-badge">Tìm thấy</span>
                                    </div>

                                    {/* Landmark Info */}
                                    <div className="result-info-modal">
                                        {result.landmark_info?.image_urls?.[0] && (
                                            <div className="result-image-modal">
                                                <img
                                                    src={result.landmark_info.image_urls[0]}
                                                    alt={result.landmark_info.name}
                                                    onError={(e) => e.target.style.display = 'none'}
                                                />
                                            </div>
                                        )}
                                        <h2>{result.landmark_info?.name || 'Địa điểm'}</h2>
                                        <p className="result-location-modal">
                                            {result.landmark_info?.location_province}
                                        </p>
                                        {result.landmark_info?.specific_address && (
                                            <p className="result-address-modal">
                                                {result.landmark_info.specific_address}
                                            </p>
                                        )}
                                    </div>

                                    {/* Share Buttons */}
                                    <ShareButtons
                                        title={`Khám phá ${result.landmark_info?.name}`}
                                        text={`Tôi vừa khám phá ${result.landmark_info?.name} với Smart Sightseeing lúc ${new Date().toLocaleString('vi-VN')} tại ${result.landmark_info?.location_province}!`}
                                        url={`${window.location.origin}/destination/${result.landmark_id}`}
                                        ogUrl={`${window.location.origin}/api/og/${result.landmark_id}`}
                                        userImageUrl={result.user_image_url}
                                        timestamp={new Date().toISOString()}
                                        compact={true}
                                    />

                                    {/* Actions */}
                                    <div className="result-actions-modal">
                                        <Link
                                            to={`/destination/${result.landmark_id}`}
                                            className="btn btn-primary btn-lg"
                                        >
                                            Xem chi tiết
                                        </Link>
                                        <button
                                            className="btn btn-secondary"
                                            onClick={resetSearch}
                                        >
                                            Tìm kiếm khác
                                        </button>
                                    </div>
                                </>
                            ) : (
                                <>
                                    <div className="confidence-box not-found">
                                        <span className="confidence-badge warning">✗ Không tìm thấy</span>
                                    </div>
                                    <p className="not-found-message">
                                        {result.message || 'Không thể nhận diện địa điểm trong ảnh'}
                                    </p>
                                    <button className="btn btn-secondary" onClick={resetSearch}>
                                        Thử ảnh khác
                                    </button>
                                </>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default VisualSearch;
