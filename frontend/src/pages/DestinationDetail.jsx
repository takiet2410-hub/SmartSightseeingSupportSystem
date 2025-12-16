import React, { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getDestinationDetail } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { addToFavorites, removeFromFavorites, isFavorite } from './Favorites';
import LoadingSpinner from '../components/LoadingSpinner';
import './DestinationDetail.css';

// Helper: Clean address that starts with comma
const cleanAddress = (address) => {
    if (!address) return null;
    return address.replace(/^[,\s]+/, '').trim() || null;
};

// Helper: Capitalize first letter
const capitalize = (str) => {
    if (!str) return str;
    return str.charAt(0).toUpperCase() + str.slice(1);
};

const DestinationDetail = () => {
    const { id } = useParams();
    const navigate = useNavigate();
    const { user, isAuthenticated } = useAuth();
    const [destination, setDestination] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [currentImage, setCurrentImage] = useState(0);
    const [isFavorited, setIsFavorited] = useState(false);
    const [isPaused, setIsPaused] = useState(false);

    useEffect(() => {
        fetchDetail();
    }, [id]);

    useEffect(() => {
        if (user?.id && id) {
            setIsFavorited(isFavorite(user.id, id));
        }
    }, [user?.id, id]);

    // Auto-slide effect
    useEffect(() => {
        if (!destination?.image_urls?.length || destination.image_urls.length <= 1) return;
        if (isPaused) return;

        const interval = setInterval(() => {
            setCurrentImage(prev => (prev + 1) % destination.image_urls.length);
        }, 4000); // Change every 4 seconds

        return () => clearInterval(interval);
    }, [destination?.image_urls?.length, isPaused]);

    const fetchDetail = async () => {
        setLoading(true);
        try {
            const data = await getDestinationDetail(id);
            setDestination(data);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const toggleFavorite = () => {
        if (!isAuthenticated) {
            navigate('/login', { state: { from: { pathname: `/destination/${id}` } } });
            return;
        }
        if (isFavorited) {
            removeFromFavorites(user.id, id);
            setIsFavorited(false);
        } else {
            addToFavorites(user.id, id);
            setIsFavorited(true);
        }
    };

    const nextImage = useCallback(() => {
        if (!destination?.image_urls?.length) return;
        setCurrentImage(prev => (prev + 1) % destination.image_urls.length);
    }, [destination?.image_urls?.length]);

    const prevImage = useCallback(() => {
        if (!destination?.image_urls?.length) return;
        setCurrentImage(prev => prev === 0 ? destination.image_urls.length - 1 : prev - 1);
    }, [destination?.image_urls?.length]);

    const goToImage = (index) => {
        setCurrentImage(index);
    };

    if (loading) {
        return (
            <div className="detail-page loading">
                <LoadingSpinner />
            </div>
        );
    }

    if (error || !destination) {
        return (
            <div className="detail-page">
                <div className="container">
                    <div className="error-state">
                        <p>{error || 'Không tìm thấy địa điểm'}</p>
                        <button className="btn btn-secondary" onClick={() => navigate('/destinations')}>
                            Quay lại
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    const images = destination.image_urls || [];
    const cleanedAddress = cleanAddress(destination.specific_address);

    return (
        <div className="detail-page">
            {/* Hero Gallery - Full Width at Top */}
            {images.length > 0 && (
                <div
                    className="hero-gallery"
                    onMouseEnter={() => setIsPaused(true)}
                    onMouseLeave={() => setIsPaused(false)}
                >
                    <div className="hero-gallery-container">
                        <img
                            src={images[currentImage]}
                            alt={destination.name}
                            className="hero-gallery-image"
                            onError={(e) => e.target.src = 'https://via.placeholder.com/1200x600?text=No+Image'}
                        />

                        {/* Navigation Arrows */}
                        {images.length > 1 && (
                            <>
                                <button
                                    className="hero-nav hero-nav-prev"
                                    onClick={prevImage}
                                    aria-label="Previous image"
                                >
                                    ‹
                                </button>
                                <button
                                    className="hero-nav hero-nav-next"
                                    onClick={nextImage}
                                    aria-label="Next image"
                                >
                                    ›
                                </button>
                            </>
                        )}

                        {/* Dots indicator */}
                        {images.length > 1 && (
                            <div className="hero-dots">
                                {images.map((_, index) => (
                                    <button
                                        key={index}
                                        className={`hero-dot ${index === currentImage ? 'active' : ''}`}
                                        onClick={() => goToImage(index)}
                                        aria-label={`Go to image ${index + 1}`}
                                    />
                                ))}
                            </div>
                        )}

                        {/* Image counter */}
                        {images.length > 1 && (
                            <div className="hero-counter">
                                {currentImage + 1} / {images.length}
                            </div>
                        )}
                    </div>
                </div>
            )}

            <div className="container">
                <button className="back-btn" onClick={() => navigate(-1)}>
                    ← Quay lại
                </button>

                <div className="detail-content">
                    {/* Header */}
                    <div className="detail-header">
                        <div className="header-main">
                            <h1>{destination.name}</h1>
                            <button
                                className={`favorite-btn ${isFavorited ? 'active' : ''}`}
                                onClick={toggleFavorite}
                            >
                                {isFavorited ? '♥' : '♡'}
                            </button>
                        </div>
                        <p className="location">{destination.location_province}</p>
                        {cleanedAddress && (
                            <p className="address">{cleanedAddress}</p>
                        )}
                        {destination.overall_rating > 0 && (
                            <div className="rating">
                                ⭐ {destination.overall_rating.toFixed(1)}
                            </div>
                        )}
                    </div>

                    <div className="detail-body">
                        {/* Main Content */}
                        <div className="main-content">
                            {/* Description */}
                            {destination.description && (
                                <div className="section">
                                    <h2>Mô tả</h2>
                                    <p className="description-text">{destination.description}</p>
                                </div>
                            )}

                            {/* Tags - Capitalize */}
                            <div className="section">
                                <h2>Thông tin</h2>
                                <div className="tags">
                                    {destination.budget_range && (
                                        <span className="tag">{capitalize(destination.budget_range)}</span>
                                    )}
                                    {destination.available_time?.map((t, i) => (
                                        <span key={i} className="tag">{capitalize(t)}</span>
                                    ))}
                                    {destination.season_tag?.map((s, i) => (
                                        <span key={i} className="tag">{capitalize(s)}</span>
                                    ))}
                                    {destination.companion_tag?.map((c, i) => (
                                        <span key={i} className="tag">{capitalize(c)}</span>
                                    ))}
                                </div>
                            </div>
                        </div>

                        {/* Sidebar - Weather only */}
                        <div className="sidebar">
                            {/* Weather */}
                            {destination.weather && (
                                <div className="weather-card">
                                    <h3>Thời tiết hiện tại</h3>
                                    <div className="weather-info">
                                        <span className="temp">{destination.weather.temp}°C</span>
                                        <span className="desc">{destination.weather.description}</span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default DestinationDetail;
