import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import './Navbar.css';

const Navbar = () => {
    const location = useLocation();
    const navigate = useNavigate();
    const { user, isAuthenticated, logout } = useAuth();
    const { isDark, toggleTheme } = useTheme();
    const [showDropdown, setShowDropdown] = useState(false);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
    const [showLoginPrompt, setShowLoginPrompt] = useState(false);
    const dropdownRef = useRef(null);

    const isActive = (path) => location.pathname === path;

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
                setShowDropdown(false);
            }
        };
        document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, []);

    const handleLogout = () => {
        logout();
        setShowDropdown(false);
        navigate('/');
    };

    const handleCheckInHistoryClick = (e) => {
        if (!isAuthenticated) {
            e.preventDefault();
            setShowLoginPrompt(true);
        }
    };

    return (
        <>
            {/* Login Prompt Modal */}
            {showLoginPrompt && (
                <div className="login-prompt-overlay" onClick={() => setShowLoginPrompt(false)}>
                    <div className="login-prompt-modal" onClick={e => e.stopPropagation()}>
                        <div className="login-prompt-icon">🔐</div>
                        <h3>Yêu cầu đăng nhập</h3>
                        <p>Vui lòng đăng nhập để xem lịch sử check-in của bạn.</p>
                        <div className="login-prompt-actions">
                            <Link to="/login" className="btn btn-primary" onClick={() => setShowLoginPrompt(false)}>
                                Đăng nhập
                            </Link>
                            <button className="btn btn-secondary" onClick={() => setShowLoginPrompt(false)}>
                                Để sau
                            </button>
                        </div>
                    </div>
                </div>
            )}

            <nav className="navbar">
                <div className="container navbar-inner">
                    <Link to="/" className="navbar-brand">
                        <span>Smart Sightseeing</span>
                    </Link>

                    {/* Desktop Menu */}
                    <div className="navbar-links">
                        <Link to="/" className={`nav-link ${isActive('/') ? 'active' : ''}`}>
                            Trang chủ
                        </Link>
                        <Link to="/destinations" className={`nav-link ${isActive('/destinations') ? 'active' : ''}`}>
                            Khám phá
                        </Link>
                        <Link to="/recommendations" className={`nav-link ${isActive('/recommendations') ? 'active' : ''}`}>
                            Gợi ý AI
                        </Link>
                        <Link to="/visual-search" className={`nav-link ${isActive('/visual-search') ? 'active' : ''}`}>
                            Tìm bằng ảnh
                        </Link>
                    </div>

                    {/* Right Section */}
                    <div className="navbar-right">
                        {/* Theme Toggle */}
                        <button className="theme-toggle" onClick={toggleTheme} title={isDark ? 'Chế độ sáng' : 'Chế độ tối'}>
                            {isDark ? (
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <circle cx="12" cy="12" r="5" />
                                    <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42" />
                                </svg>
                            ) : (
                                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
                                </svg>
                            )}
                        </button>

                        {/* Auth */}
                        {isAuthenticated ? (
                            <div className="user-menu" ref={dropdownRef}>
                                <button
                                    className="user-btn"
                                    onClick={() => setShowDropdown(!showDropdown)}
                                >
                                    <span className="user-avatar">
                                        {(user?.fullName || user?.username || '?').charAt(0).toUpperCase()}
                                    </span>
                                </button>

                                {showDropdown && (
                                    <div className="dropdown animate-fade-in">
                                        <div className="dropdown-header">
                                            <span className="dropdown-name">{user?.fullName || user?.username}</span>
                                        </div>
                                        <div className="dropdown-divider"></div>
                                        <Link to="/profile" className="dropdown-item" onClick={() => setShowDropdown(false)}>
                                            Trang cá nhân
                                        </Link>
                                        <Link to="/favorites" className="dropdown-item" onClick={() => setShowDropdown(false)}>
                                            Yêu thích
                                        </Link>
                                        <div className="dropdown-divider"></div>
                                        <span className="dropdown-label">Album & Du lịch</span>
                                        <Link to="/album-creator" className="dropdown-item" onClick={() => setShowDropdown(false)}>
                                            Tạo Album
                                        </Link>
                                        <Link to="/my-albums" className="dropdown-item" onClick={() => setShowDropdown(false)}>
                                            Album của tôi
                                        </Link>
                                        <Link to="/trip-summary" className="dropdown-item" onClick={() => setShowDropdown(false)}>
                                            Tổng kết chuyến đi
                                        </Link>
                                        <Link to="/detection-history" className="dropdown-item" onClick={() => setShowDropdown(false)}>
                                            Lịch sử nhận diện
                                        </Link>
                                        <div className="dropdown-divider"></div>
                                        <button className="dropdown-item logout" onClick={handleLogout}>
                                            Đăng xuất
                                        </button>
                                    </div>
                                )}
                            </div>
                        ) : (
                            <Link to="/login" className="btn btn-primary">
                                Đăng nhập
                            </Link>
                        )}
                    </div>

                    {/* Mobile Menu Button */}
                    <button
                        className="mobile-menu-btn"
                        onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                    >
                        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            {mobileMenuOpen ? (
                                <path d="M6 18L18 6M6 6l12 12" />
                            ) : (
                                <path d="M4 6h16M4 12h16M4 18h16" />
                            )}
                        </svg>
                    </button>
                </div>

                {/* Mobile Menu */}
                {mobileMenuOpen && (
                    <div className="mobile-menu animate-fade-in">
                        <Link to="/" className="mobile-link" onClick={() => setMobileMenuOpen(false)}>Trang chủ</Link>
                        <Link to="/destinations" className="mobile-link" onClick={() => setMobileMenuOpen(false)}>Khám phá</Link>
                        <Link to="/recommendations" className="mobile-link" onClick={() => setMobileMenuOpen(false)}>Gợi ý AI</Link>
                        <Link to="/visual-search" className="mobile-link" onClick={() => setMobileMenuOpen(false)}>Tìm bằng ảnh</Link>
                        <button className="mobile-link" onClick={() => { toggleTheme(); }}>
                            {isDark ? 'Chế độ sáng' : 'Chế độ tối'}
                        </button>
                        {isAuthenticated ? (
                            <>
                                <Link to="/profile" className="mobile-link" onClick={() => setMobileMenuOpen(false)}>Trang cá nhân</Link>
                                <Link to="/favorites" className="mobile-link" onClick={() => setMobileMenuOpen(false)}>Yêu thích</Link>
                                <div className="mobile-divider"></div>
                                <Link to="/album-creator" className="mobile-link" onClick={() => setMobileMenuOpen(false)}>Tạo Album</Link>
                                <Link to="/my-albums" className="mobile-link" onClick={() => setMobileMenuOpen(false)}>Album của tôi</Link>
                                <Link to="/trip-summary" className="mobile-link" onClick={() => setMobileMenuOpen(false)}>Tổng kết chuyến đi</Link>
                                <Link to="/detection-history" className="mobile-link" onClick={() => setMobileMenuOpen(false)}>Lịch sử nhận diện</Link>
                                <div className="mobile-divider"></div>
                                <button className="mobile-link logout" onClick={() => { handleLogout(); setMobileMenuOpen(false); }}>Đăng xuất</button>
                            </>
                        ) : (
                            <Link to="/login" className="mobile-link accent" onClick={() => setMobileMenuOpen(false)}>Đăng nhập</Link>
                        )}
                    </div>
                )}
            </nav>
        </>
    );
};

export default Navbar;
