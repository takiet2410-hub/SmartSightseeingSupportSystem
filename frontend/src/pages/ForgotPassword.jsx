import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './ForgotPassword.css';

const ForgotPassword = () => {
    const { forgotPassword, loading, error, clearError } = useAuth();

    const [formData, setFormData] = useState({
        username: '',
        email: ''
    });
    const [formError, setFormError] = useState('');
    const [success, setSuccess] = useState(false);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: value
        }));
        setFormError('');
        clearError();
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        setFormError('');

        if (!formData.username.trim()) {
            setFormError('Vui lòng nhập tên đăng nhập');
            return;
        }
        if (!formData.email.trim()) {
            setFormError('Vui lòng nhập email');
            return;
        }
        if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
            setFormError('Email không hợp lệ');
            return;
        }

        const result = await forgotPassword(formData.username, formData.email);

        if (result.success) {
            setSuccess(true);
        }
    };

    if (success) {
        return (
            <div className="auth-page">
                <div className="auth-container">
                    <div className="auth-card success-card">
                        <div className="success-icon">📧</div>
                        <h2>Email đã được gửi!</h2>
                        <p>Vui lòng kiểm tra hộp thư của bạn để đặt lại mật khẩu.</p>
                        <p className="email-hint">Email: <strong>{formData.email}</strong></p>
                        <Link to="/login" className="btn btn-primary" style={{ marginTop: '1.5rem' }}>
                            Quay lại đăng nhập
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-page">
            <div className="auth-container">
                <div className="auth-card">
                    <div className="auth-header">
                        <div className="auth-logo">
                            <span className="logo-icon">🔑</span>
                        </div>
                        <h1>Quên mật khẩu</h1>
                        <p>Nhập thông tin để nhận email khôi phục</p>
                    </div>

                    <form onSubmit={handleSubmit} className="auth-form">
                        {(formError || error) && (
                            <div className="form-error">
                                <span>⚠️</span>
                                {formError || error}
                            </div>
                        )}

                        <div className="form-group">
                            <label htmlFor="username">Tên đăng nhập</label>
                            <div className="input-wrapper">
                                <span className="input-icon">👤</span>
                                <input
                                    type="text"
                                    id="username"
                                    name="username"
                                    value={formData.username}
                                    onChange={handleChange}
                                    placeholder="Nhập tên đăng nhập..."
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="email">Email đã đăng ký</label>
                            <div className="input-wrapper">
                                <span className="input-icon">📧</span>
                                <input
                                    type="email"
                                    id="email"
                                    name="email"
                                    value={formData.email}
                                    onChange={handleChange}
                                    placeholder="Nhập email đã đăng ký..."
                                />
                            </div>
                        </div>

                        <button
                            type="submit"
                            className="btn btn-primary btn-submit"
                            disabled={loading}
                        >
                            {loading ? (
                                <>
                                    <span className="spinner-small"></span>
                                    Đang gửi...
                                </>
                            ) : (
                                <>
                                    <span>📨</span>
                                    Gửi email khôi phục
                                </>
                            )}
                        </button>
                    </form>

                    <div className="auth-footer">
                        <p>
                            Nhớ mật khẩu rồi?{' '}
                            <Link to="/login">Đăng nhập</Link>
                        </p>
                    </div>
                </div>

                <div className="auth-decoration">
                    <div className="decoration-circle circle-1"></div>
                    <div className="decoration-circle circle-2"></div>
                    <div className="decoration-circle circle-3"></div>
                </div>
            </div>
        </div>
    );
};

export default ForgotPassword;
