import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import './Login.css';

const Register = () => {
    const navigate = useNavigate();
    const { register, loading, error, clearError } = useAuth();

    const [formData, setFormData] = useState({
        username: '',
        email: '',
        password: '',
        confirmPassword: ''
    });
    const [formError, setFormError] = useState('');
    const [success, setSuccess] = useState(false);

    const handleChange = (e) => {
        const { name, value } = e.target;
        setFormData(prev => ({ ...prev, [name]: value }));
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
        if (formData.username.length < 3) {
            setFormError('Tên đăng nhập phải có ít nhất 3 ký tự');
            return;
        }
        if (!formData.email.trim() || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
            setFormError('Email không hợp lệ');
            return;
        }
        if (formData.password.length < 6) {
            setFormError('Mật khẩu phải có ít nhất 6 ký tự');
            return;
        }
        if (formData.password !== formData.confirmPassword) {
            setFormError('Mật khẩu xác nhận không khớp');
            return;
        }

        const result = await register(formData.username, formData.password, formData.email);
        if (result.success) {
            setSuccess(true);
            setTimeout(() => navigate('/login'), 2000);
        }
    };

    if (success) {
        return (
            <div className="auth-page">
                <div className="auth-card success-card">
                    <div className="success-icon">✅</div>
                    <h2>Đăng ký thành công!</h2>
                    <p>Đang chuyển hướng...</p>
                </div>
            </div>
        );
    }

    return (
        <div className="auth-page">
            <div className="auth-card">
                <div className="auth-header">
                    <h1>Đăng ký</h1>
                    <p>Tạo tài khoản mới</p>
                </div>

                <form onSubmit={handleSubmit} className="auth-form">
                    {(formError || error) && (
                        <div className="form-error">{formError || error}</div>
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
                        <label htmlFor="email">Email</label>
                        <input
                            type="email"
                            id="email"
                            name="email"
                            className="input"
                            value={formData.email}
                            onChange={handleChange}
                            placeholder="Nhập email"
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
                            placeholder="Ít nhất 6 ký tự"
                        />
                    </div>

                    <div className="form-group">
                        <label htmlFor="confirmPassword">Xác nhận mật khẩu</label>
                        <input
                            type="password"
                            id="confirmPassword"
                            name="confirmPassword"
                            className="input"
                            value={formData.confirmPassword}
                            onChange={handleChange}
                            placeholder="Nhập lại mật khẩu"
                        />
                    </div>

                    <button
                        type="submit"
                        className="btn btn-primary btn-lg btn-submit"
                        disabled={loading}
                    >
                        {loading ? 'Đang xử lý...' : 'Đăng ký'}
                    </button>
                </form>

                <div className="auth-footer">
                    <p>
                        Đã có tài khoản? <Link to="/login">Đăng nhập</Link>
                    </p>
                </div>
            </div>
        </div>
    );
};

export default Register;
