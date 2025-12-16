import React, { useState } from 'react';
import { Link, useSearchParams, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './ResetPassword.css';

const ResetPassword = () => {
    const [searchParams] = useSearchParams();
    const navigate = useNavigate();
    const { resetPassword, loading, error, clearError } = useAuth();

    const token = searchParams.get('token');

    const [formData, setFormData] = useState({
        newPassword: '',
        confirmPassword: ''
    });
    const [formError, setFormError] = useState('');
    const [success, setSuccess] = useState(false);

    // If no token, show error
    if (!token) {
        return (
            <div className="auth-page">
                <div className="auth-container">
                    <div className="auth-card error-card">
                        <div className="error-icon">❌</div>
                        <h2>Link không hợp lệ</h2>
                        <p>Link đặt lại mật khẩu không hợp lệ hoặc đã hết hạn.</p>
                        <Link to="/forgot-password" className="btn btn-primary" style={{ marginTop: '1.5rem' }}>
                            Yêu cầu link mới
                        </Link>
                    </div>
                </div>
            </div>
        );
    }

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

        if (!formData.newPassword) {
            setFormError('Vui lòng nhập mật khẩu mới');
            return;
        }
        if (formData.newPassword.length < 6) {
            setFormError('Mật khẩu phải có ít nhất 6 ký tự');
            return;
        }
        if (formData.newPassword !== formData.confirmPassword) {
            setFormError('Mật khẩu xác nhận không khớp');
            return;
        }

        const result = await resetPassword(token, formData.newPassword, formData.confirmPassword);

        if (result.success) {
            setSuccess(true);
            setTimeout(() => {
                navigate('/login');
            }, 3000);
        }
    };

    if (success) {
        return (
            <div className="auth-page">
                <div className="auth-container">
                    <div className="auth-card success-card">
                        <div className="success-icon">✅</div>
                        <h2>Đặt lại mật khẩu thành công!</h2>
                        <p>Đang chuyển hướng đến trang đăng nhập...</p>
                        <div className="success-spinner"></div>
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
                            <span className="logo-icon">🔐</span>
                        </div>
                        <h1>Đặt lại mật khẩu</h1>
                        <p>Nhập mật khẩu mới cho tài khoản của bạn</p>
                    </div>

                    <form onSubmit={handleSubmit} className="auth-form">
                        {(formError || error) && (
                            <div className="form-error">
                                <span>⚠️</span>
                                {formError || error}
                            </div>
                        )}

                        <div className="form-group">
                            <label htmlFor="newPassword">Mật khẩu mới</label>
                            <div className="input-wrapper">
                                <span className="input-icon">🔒</span>
                                <input
                                    type="password"
                                    id="newPassword"
                                    name="newPassword"
                                    value={formData.newPassword}
                                    onChange={handleChange}
                                    placeholder="Nhập mật khẩu mới (ít nhất 6 ký tự)..."
                                    autoComplete="new-password"
                                />
                            </div>
                        </div>

                        <div className="form-group">
                            <label htmlFor="confirmPassword">Xác nhận mật khẩu</label>
                            <div className="input-wrapper">
                                <span className="input-icon">🔐</span>
                                <input
                                    type="password"
                                    id="confirmPassword"
                                    name="confirmPassword"
                                    value={formData.confirmPassword}
                                    onChange={handleChange}
                                    placeholder="Nhập lại mật khẩu mới..."
                                    autoComplete="new-password"
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
                                    Đang xử lý...
                                </>
                            ) : (
                                <>
                                    <span>✨</span>
                                    Đặt lại mật khẩu
                                </>
                            )}
                        </button>
                    </form>

                    <div className="auth-footer">
                        <p>
                            <Link to="/login">Quay lại đăng nhập</Link>
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

export default ResetPassword;
