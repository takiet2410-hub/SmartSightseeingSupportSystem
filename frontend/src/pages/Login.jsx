import React, { useState } from 'react';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { GoogleOAuthProvider, GoogleLogin } from '@react-oauth/google';
import { useAuth } from '../context/AuthContext';
import './Login.css';

// Google Client ID from environment or placeholder
const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID || '';

const Login = () => {
    const navigate = useNavigate();
    const location = useLocation();
    const { login, loginWithGoogle, loading, error, clearError } = useAuth();

    const [formData, setFormData] = useState({
        username: '',
        password: '',
        rememberMe: false
    });
    const [formError, setFormError] = useState('');

    const from = location.state?.from?.pathname || '/';

    const handleChange = (e) => {
        const { name, value, type, checked } = e.target;
        setFormData(prev => ({
            ...prev,
            [name]: type === 'checkbox' ? checked : value
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
        if (!formData.password) {
            setFormError('Vui lòng nhập mật khẩu');
            return;
        }

        const result = await login(formData.username, formData.password, formData.rememberMe);
        if (result.success) {
            navigate(from, { replace: true });
        }
    };

    // Google Login Success
    const handleGoogleSuccess = async (credentialResponse) => {
        const result = await loginWithGoogle(credentialResponse.credential);
        if (result.success) {
            navigate(from, { replace: true });
        }
    };

    // Google Login Error
    const handleGoogleError = () => {
        setFormError('Đăng nhập Google thất bại. Vui lòng thử lại.');
    };

    const hasGoogleId = !!GOOGLE_CLIENT_ID;

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-header">
                    <h1>Đăng nhập</h1>
                    <p>Chào mừng bạn quay lại</p>
                </div>

                <form onSubmit={handleSubmit} className="auth-form">
                    {(formError || error) && (
                        <div className="form-error">
                            {formError || error}
                        </div>
                    )}

                    <div className="form-group">
                        <label htmlFor="username">Tên đăng nhập</label>
                        <input
                            type="text"
                            id="username"
                            name="username"
                            className="input"
                            value={formData.username}
                            onChange={handleChange}
                            placeholder="Nhập tên đăng nhập"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="password">Mật khẩu</label>
                        <input
                            type="password"
                            id="password"
                            name="password"
                            className="input"
                            value={formData.password}
                            onChange={handleChange}
                            placeholder="Nhập mật khẩu"
                        />
                    </div>

                    <div className="form-row">
                        <label className="checkbox-label">
                            <input
                                type="checkbox"
                                name="rememberMe"
                                checked={formData.rememberMe}
                                onChange={handleChange}
                            />
                            Ghi nhớ đăng nhập
                        </label>
                        <Link to="/forgot-password" className="forgot-link">
                            Quên mật khẩu?
                        </Link>
                    </div>

                    <button
                        type="submit"
                        className="btn btn-primary btn-lg btn-submit"
                        disabled={loading}
                    >
                        {loading ? 'Đang xử lý...' : 'Đăng nhập'}
                    </button>
                </form>

                {/* OAuth Section - Google Only */}
                {hasGoogleId && (
                    <>
                        <div className="auth-divider">
                            <span>hoặc</span>
                        </div>

                        <div className="social-buttons">
                            <GoogleOAuthProvider clientId={GOOGLE_CLIENT_ID}>
                                <GoogleLogin
                                    onSuccess={handleGoogleSuccess}
                                    onError={handleGoogleError}
                                    theme="outline"
                                    size="large"
                                    width="100%"
                                    text="signin_with"
                                    shape="rectangular"
                                />
                            </GoogleOAuthProvider>
                        </div>
                    </>
                )}

                {/* No OAuth configured message */}
                {!hasGoogleId && (
                    <div className="oauth-notice">
                        <p>Đăng nhập bằng Google chưa được cấu hình.</p>
                    </div>
                )}

                <div className="auth-footer">
                    <p>
                        Chưa có tài khoản? <Link to="/register">Đăng ký</Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Login;
