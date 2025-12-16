import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { getDestinationDetail } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import './Favorites.css';

const FAVORITES_KEY = 'user_favorites';

const getFavoritesFromStorage = (userId) => {
    const stored = localStorage.getItem(`${FAVORITES_KEY}_${userId}`);
    return stored ? JSON.parse(stored) : [];
};

const saveFavoritesToStorage = (userId, favorites) => {
    localStorage.setItem(`${FAVORITES_KEY}_${userId}`, JSON.stringify(favorites));
};

const Favorites = () => {
    const { user } = useAuth();
    const [favorites, setFavorites] = useState([]);
    const [destinations, setDestinations] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const loadFavorites = async () => {
            if (!user?.id) return;

            setLoading(true);
            const favoriteIds = getFavoritesFromStorage(user.id);
            setFavorites(favoriteIds);

            if (favoriteIds.length > 0) {
                const results = await Promise.all(
                    favoriteIds.map(id => getDestinationDetail(id).catch(() => null))
                );
                setDestinations(results.filter(d => d !== null));
            }

            setLoading(false);
        };

        loadFavorites();
    }, [user?.id]);

    const removeFavorite = (landmarkId) => {
        const newFavorites = favorites.filter(id => id !== landmarkId);
        setFavorites(newFavorites);
        setDestinations(prev => prev.filter(d => d.id !== landmarkId));
        saveFavoritesToStorage(user.id, newFavorites);
    };

    if (loading) {
        return (
            <div className="favorites-page">
                <div className="container"><LoadingSpinner /></div>
            </div>
        );
    }

    return (
        <div className="favorites-page">
            <div className="container">
                <div className="page-header">
                    <h1>Yêu thích</h1>
                    <p>Các địa điểm bạn đã lưu</p>
                </div>

                {destinations.length === 0 ? (
                    <div className="empty-state">
                        <p>Chưa có địa điểm yêu thích nào</p>
                        <Link to="/destinations" className="btn btn-primary">
                            Khám phá ngay
                        </Link>
                    </div>
                ) : (
                    <div className="favorites-grid">
                        {destinations.map(dest => (
                            <div key={dest.id} className="favorite-card">
                                <div className="card-image">
                                    <img
                                        src={dest.image_urls?.[0] || 'https://via.placeholder.com/400x300'}
                                        alt={dest.name}
                                        onError={(e) => e.target.src = 'https://via.placeholder.com/400x300'}
                                    />
                                    <button
                                        className="remove-btn"
                                        onClick={() => removeFavorite(dest.id)}
                                    >
                                        ✕
                                    </button>
                                </div>
                                <div className="card-content">
                                    <h3>{dest.name}</h3>
                                    <p>📍 {dest.location_province}</p>
                                    <Link to={`/destination/${dest.id}`} className="btn btn-secondary">
                                        Xem chi tiết
                                    </Link>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </div>
    );
};

export const addToFavorites = (userId, landmarkId) => {
    const favorites = getFavoritesFromStorage(userId);
    if (!favorites.includes(landmarkId)) {
        favorites.push(landmarkId);
        saveFavoritesToStorage(userId, favorites);
    }
    return favorites;
};

export const removeFromFavorites = (userId, landmarkId) => {
    const favorites = getFavoritesFromStorage(userId);
    const newFavorites = favorites.filter(id => id !== landmarkId);
    saveFavoritesToStorage(userId, newFavorites);
    return newFavorites;
};

export const isFavorite = (userId, landmarkId) => {
    if (!userId) return false;
    return getFavoritesFromStorage(userId).includes(landmarkId);
};

export default Favorites;
