import React from 'react';
import { Link } from 'react-router-dom';
import './Home.css';

const Home = () => {
    return (
        <div className="home">
            {/* Hero */}
            <section className="hero">
                <div className="container">
                    <div className="hero-content animate-slide-up">
                        <div className="hero-badge">
                            <span></span> Khám phá hơn 900+ địa điểm
                        </div>
                        <h1>Du lịch thông minh<br />cùng AI</h1>
                        <p>Tìm kiếm địa điểm hoàn hảo với sức mạnh của trí tuệ nhân tạo</p>
                        <div className="hero-actions">
                            <Link to="/destinations" className="btn btn-primary btn-lg">
                                Bắt đầu khám phá
                            </Link>
                            <Link to="/visual-search" className="btn btn-secondary btn-lg">
                                Tìm bằng ảnh
                            </Link>
                        </div>
                    </div>
                </div>
            </section>

            {/* Features */}
            <section className="features">
                <div className="container">
                    <div className="features-grid">
                        <Link to="/recommendations" className="feature-card">
                            <div className="feature-icon"></div>
                            <h3>Gợi ý thông minh</h3>
                            <p>Mô tả sở thích, AI tìm địa điểm phù hợp nhất</p>
                        </Link>
                        <Link to="/visual-search" className="feature-card">
                            <div className="feature-icon"></div>
                            <h3>Nhận diện hình ảnh</h3>
                            <p>Upload ảnh, AI nhận diện địa điểm ngay lập tức</p>
                        </Link>
                        <Link to="/destinations" className="feature-card">
                            <div className="feature-icon"></div>
                            <h3>Bộ lọc chi tiết</h3>
                            <p>Ngân sách, thời gian, mùa, người đi cùng</p>
                        </Link>
                    </div>
                </div>
            </section>

            {/* CTA */}
            <section className="cta">
                <div className="container">
                    <div className="cta-content">
                        <h2>Sẵn sàng khám phá?</h2>
                        <p>Để AI giúp bạn tìm điểm đến hoàn hảo</p>
                        <Link to="/recommendations" className="btn btn-primary btn-lg">
                            Nhận gợi ý từ AI
                        </Link>
                    </div>
                </div>
            </section>
        </div>
    );
};

export default Home;
