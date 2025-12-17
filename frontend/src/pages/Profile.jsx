import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Profile.css';

const Profile = () => {
    const { user } = useAuth();

    return (
        <div className="profile-page">
            <div className="container">
                <div className="profile-card">
                    <div className="profile-header">
                        <div className="profile-avatar">
                            {(user?.fullName || user?.username || '?').charAt(0).toUpperCase()}
                        </div>
                        <div className="profile-info">
                            <h1>{user?.fullName || user?.username}</h1>
                            <p>@{user?.username}</p>
                        </div>
                    </div>

                    <div className="profile-section">
                        <h2>Tài khoản</h2>
                        <div className="info-list">
                            <div className="info-item">
                                <span className="label">Tên đăng nhập</span>
                                <span className="value">{user?.username}</span>
                            </div>
                            <div className="info-item">
                                <span className="label">Loại tài khoản</span>
                                <span className="value">{user?.authProvider || 'local'}</span>
                            </div>
                        </div>
                    </div>

                    <div className="profile-section">
                        <h2>Truy cập nhanh</h2>
                        <div className="quick-links">
                            <Link to="/favorites" className="quick-link">
                                Yêu thích
                            </Link>
                            <Link to="/destinations" className="quick-link">
                                Khám phá
                            </Link>
                            <Link to="/recommendations" className="quick-link">
                                Gợi ý AI
                            </Link>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Profile;
