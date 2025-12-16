import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getSharedAlbum } from '../services/afterService';
import LoadingSpinner from '../components/LoadingSpinner';
import './SharedAlbum.css';

const SharedAlbum = () => {
    const { shareToken } = useParams();
    const [album, setAlbum] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedPhoto, setSelectedPhoto] = useState(null);

    useEffect(() => {
        const fetchAlbum = async () => {
            try {
                setLoading(true);
                const data = await getSharedAlbum(shareToken);
                setAlbum(data);
            } catch (err) {
                setError(err.response?.status === 404
                    ? 'Album không tồn tại hoặc link đã hết hạn'
                    : 'Không thể tải album');
            } finally {
                setLoading(false);
            }
        };

        if (shareToken) {
            fetchAlbum();
        }
    }, [shareToken]);

    if (loading) {
        return (
            <div className="shared-album-page">
                <div className="container">
                    <LoadingSpinner text="Đang tải album..." />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="shared-album-page">
                <div className="container">
                    <div className="error-state">
                        <div className="error-icon">🔒</div>
                        <h2>Không thể truy cập</h2>
                        <p>{error}</p>
                        <Link to="/" className="btn btn-primary">
                            Về trang chủ
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="shared-album-page">
            <div className="container">
                {/* Header */}
                <div className="album-header">
                    {album.cover_photo_url && (
                        <div className="cover-image">
                            <img src={album.cover_photo_url} alt={album.title} />
                        </div>
                    )}
                    <div className="album-info">
                        <h1>{album.title}</h1>
                        <p className="photo-count">{album.photos?.length || 0} ảnh</p>
                        {album.download_zip_url && (
                            <a
                                href={album.download_zip_url}
                                className="btn btn-primary download-btn"
                                target="_blank"
                                rel="noopener noreferrer"
                            >
                                📥 Tải toàn bộ album
                            </a>
                        )}
                    </div>
                </div>

                {/* Photo Grid */}
                <div className="photos-grid">
                    {album.photos?.map((photo, index) => (
                        <div
                            key={photo.id || index}
                            className="photo-item"
                            onClick={() => setSelectedPhoto(photo)}
                        >
                            <img src={photo.image_url} alt={photo.filename} />
                            {photo.timestamp && (
                                <div className="photo-date">
                                    {new Date(photo.timestamp).toLocaleDateString('vi-VN')}
                                </div>
                            )}
                        </div>
                    ))}
                </div>

                {/* Lightbox */}
                {selectedPhoto && (
                    <div className="lightbox" onClick={() => setSelectedPhoto(null)}>
                        <div className="lightbox-content" onClick={e => e.stopPropagation()}>
                            <button className="close-btn" onClick={() => setSelectedPhoto(null)}>
                                ✕
                            </button>
                            <img src={selectedPhoto.image_url} alt={selectedPhoto.filename} />
                            {selectedPhoto.timestamp && (
                                <p className="photo-timestamp">
                                    {new Date(selectedPhoto.timestamp).toLocaleString('vi-VN')}
                                </p>
                            )}
                        </div>
                    </div>
                )}

                {/* Branding */}
                <div className="shared-branding">
                    <p>Được chia sẻ bởi <Link to="/">Smart Sightseeing</Link></p>
                </div>
            </div>
        </div>
    );
};

export default SharedAlbum;
