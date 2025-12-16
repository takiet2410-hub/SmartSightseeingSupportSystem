import { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { createAlbum } from '../services/afterService';
import { useAuth } from '../context/AuthContext';
import { useNavigate } from 'react-router-dom';
import './AlbumCreator.css';

const AlbumCreator = () => {
    const { user } = useAuth();
    const navigate = useNavigate();
    const [files, setFiles] = useState([]);
    const [uploading, setUploading] = useState(false);
    const [progress, setProgress] = useState(0);
    const [albums, setAlbums] = useState([]);
    const [error, setError] = useState(null);
    const [stage, setStage] = useState('upload'); // upload, processing, done
    const [selectedAlbum, setSelectedAlbum] = useState(null); // For viewing album details

    const onDrop = useCallback((acceptedFiles) => {
        const imageFiles = acceptedFiles.filter(file =>
            file.type.startsWith('image/')
        );
        setFiles(prev => [...prev, ...imageFiles]);
        setError(null);
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop,
        accept: { 'image/*': ['.jpg', '.jpeg', '.png', '.heic', '.heif'] },
        maxSize: 50 * 1024 * 1024, // 50MB
    });

    const removeFile = (index) => {
        setFiles(prev => prev.filter((_, i) => i !== index));
    };

    const handleUpload = async () => {
        if (!user) {
            setError('Vui lòng đăng nhập để tạo album');
            return;
        }

        if (files.length === 0) {
            setError('Vui lòng chọn ít nhất 1 ảnh');
            return;
        }

        setUploading(true);
        setStage('processing');
        setError(null);

        try {
            const result = await createAlbum(files, (percent) => {
                setProgress(percent);
            });

            setAlbums(result.albums || []);
            setStage('done');
        } catch (err) {
            setError(err.message || 'Có lỗi xảy ra khi tạo album');
            setStage('upload');
        } finally {
            setUploading(false);
        }
    };

    const resetUpload = () => {
        setFiles([]);
        setAlbums([]);
        setProgress(0);
        setStage('upload');
        setError(null);
    };

    if (!user) {
        return (
            <div className="album-creator">
                <div className="auth-required">
                    <h2>Yêu cầu đăng nhập</h2>
                    <p>Bạn cần đăng nhập để sử dụng tính năng tạo album.</p>
                    <button onClick={() => navigate('/login')} className="login-btn">
                        Đăng nhập ngay
                    </button>
                </div>
            </div>
        );
    }

    return (
        <div className="album-creator">
            <div className="page-header">
                <h1>Tạo Album Ảnh</h1>
                <p>Upload ảnh chuyến đi để AI tự động phân loại và tạo album</p>
            </div>

            {error && <div className="error-message">{error}</div>}

            {stage === 'upload' && (
                <>
                    <div {...getRootProps()} className={`dropzone ${isDragActive ? 'active' : ''}`}>
                        <input {...getInputProps()} />
                        <div className="dropzone-content">
                            <span className="upload-icon"></span>
                            {isDragActive ? (
                                <p>Thả ảnh vào đây...</p>
                            ) : (
                                <>
                                    <p>Kéo thả ảnh vào đây</p>
                                    <p className="or-text">hoặc click để chọn</p>
                                </>
                            )}
                            <span className="hint">Hỗ trợ: JPG, PNG (tối đa 50MB/ảnh, 500 ảnh)</span>
                        </div>
                    </div>

                    {files.length > 0 && (
                        <div className="preview-section">
                            <div className="preview-header">
                                <h3>Đã chọn {files.length} ảnh</h3>
                                <button onClick={() => setFiles([])} className="clear-btn">Xóa tất cả</button>
                            </div>
                            <div className="preview-grid">
                                {files.slice(0, 20).map((file, index) => (
                                    <div key={index} className="preview-item">
                                        <img src={URL.createObjectURL(file)} alt={file.name} />
                                        <button className="remove-btn" onClick={() => removeFile(index)}>×</button>
                                        <span className="file-name">{file.name}</span>
                                    </div>
                                ))}
                                {files.length > 20 && (
                                    <div className="preview-more">+{files.length - 20} ảnh khác</div>
                                )}
                            </div>
                            <button
                                className="upload-btn"
                                onClick={handleUpload}
                                disabled={uploading}
                            >
                                Tạo Album ({files.length} ảnh)
                            </button>
                        </div>
                    )}
                </>
            )}

            {stage === 'processing' && (
                <div className="processing-section">
                    <div className="processing-animation">
                        <div className="spinner"></div>
                    </div>
                    <h3>Đang xử lý ảnh...</h3>
                    <div className="progress-bar">
                        <div className="progress-fill" style={{ width: `${progress}%` }}></div>
                    </div>
                    <p className="progress-text">{progress}% - Upload ảnh lên server</p>
                    <p className="processing-hint">AI đang phân tích: Loại bỏ ảnh xấu, nhóm theo địa điểm...</p>
                </div>
            )}

            {stage === 'done' && (
                <div className="results-section">
                    <div className="success-header">
                        <span className="success-icon"></span>
                        <h2>Tạo album thành công!</h2>
                        <p>Đã tạo {albums.filter(a => a.method !== 'filters_rejected').length} album từ {files.length} ảnh</p>
                    </div>

                    <div className="albums-grid">
                        {albums.filter(a => a.method !== 'filters_rejected').map((album) => (
                            <div
                                key={album.id}
                                className="album-card"
                                onClick={() => setSelectedAlbum(album)}
                                style={{ cursor: 'pointer' }}
                            >
                                <div className="album-cover">
                                    {album.cover_photo_url ? (
                                        <img src={album.cover_photo_url} alt={album.title} />
                                    ) : (
                                        <div className="no-cover"></div>
                                    )}
                                </div>
                                <div className="album-info">
                                    <h4>{album.title}</h4>
                                    <p>{album.photos?.length || 0} ảnh</p>
                                    <span className="album-method">{album.method}</span>
                                </div>
                                {album.download_zip_url && (
                                    <a
                                        href={album.download_zip_url}
                                        className="download-btn"
                                        target="_blank"
                                        rel="noopener noreferrer"
                                        onClick={(e) => e.stopPropagation()}
                                    >
                                        Tải về ZIP
                                    </a>
                                )}
                            </div>
                        ))}
                    </div>

                    {albums.some(a => a.method === 'filters_rejected') && (
                        <div className="rejected-section">
                            <h4>Ảnh bị loại ({albums.find(a => a.method === 'filters_rejected')?.photos?.length || 0})</h4>
                            <p>Các ảnh này bị loại do chất lượng kém hoặc không phù hợp</p>
                        </div>
                    )}

                    <div className="action-buttons">
                        <button onClick={resetUpload} className="new-upload-btn">
                            Upload thêm ảnh
                        </button>
                        <button onClick={() => navigate('/my-albums')} className="view-albums-btn">
                            Xem tất cả album
                        </button>
                    </div>
                </div>
            )}

            {/* Album Detail Modal */}
            {selectedAlbum && (
                <div className="modal-overlay" onClick={() => setSelectedAlbum(null)}>
                    <div className="modal-content" onClick={e => e.stopPropagation()}>
                        <button className="close-btn" onClick={() => setSelectedAlbum(null)}>×</button>

                        <h2>{selectedAlbum.title}</h2>
                        <p className="modal-meta">
                            {selectedAlbum.photos?.length || 0} ảnh •
                            Phương thức: {selectedAlbum.method}
                        </p>

                        {/* Photos Grid */}
                        <div className="photos-grid">
                            {selectedAlbum.photos?.map((photo, index) => (
                                <div key={photo.id || index} className="photo-item">
                                    <img src={photo.image_url} alt={photo.filename} />
                                </div>
                            ))}
                        </div>

                        {/* Actions */}
                        <div className="album-actions">
                            {selectedAlbum.download_zip_url && (
                                <a
                                    href={selectedAlbum.download_zip_url}
                                    className="action-btn download"
                                    target="_blank"
                                    rel="noopener noreferrer"
                                >
                                    Tải về ZIP
                                </a>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default AlbumCreator;
