import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { getRecommendations } from '../services/api';
import LoadingSpinner from '../components/LoadingSpinner';
import './AIRecommendations.css';

const EXAMPLE_PROMPTS = [
    'Tôi muốn đi biển nghỉ dưỡng cuối tuần',
    'Du lịch núi mát mẻ cho gia đình',
    'Địa điểm chụp ảnh đẹp ở miền Bắc',
    'Đi chơi cùng bạn bè, ngân sách thấp'
];

const AIRecommendations = () => {
    const [prompt, setPrompt] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    const [recommendations, setRecommendations] = useState([]);
    const [status, setStatus] = useState('');

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!prompt.trim()) return;

        setLoading(true);
        setError(null);
        setRecommendations([]);

        try {
            const data = await getRecommendations(prompt);
            setStatus(data.status);
            setRecommendations(data.recommendations || []);
        } catch (err) {
            setError(err.message);
        } finally {
            setLoading(false);
        }
    };

    const handleExampleClick = (example) => {
        setPrompt(example);
    };

    return (
        <div className="ai-page">
            <div className="container">
                <div className="page-header">
                    <h1>Gợi ý bằng AI</h1>
                    <p>Mô tả sở thích của bạn, AI sẽ tìm địa điểm phù hợp</p>
                </div>

                {/* Search Form */}
                <form onSubmit={handleSubmit} className="search-form">
                    <textarea
                        className="input prompt-input"
                        placeholder="Ví dụ: Tôi muốn đi du lịch biển, thích chụp ảnh đẹp, ngân sách trung bình..."
                        value={prompt}
                        onChange={(e) => setPrompt(e.target.value)}
                        rows={3}
                    />
                    <button
                        type="submit"
                        className="btn btn-primary btn-lg"
                        disabled={loading || !prompt.trim()}
                    >
                        {loading ? 'Đang tìm...' : 'Tìm kiếm'}
                    </button>
                </form>

                {/* Example Prompts */}
                {!loading && recommendations.length === 0 && (
                    <div className="examples">
                        <p className="examples-label">Thử các gợi ý:</p>
                        <div className="examples-list">
                            {EXAMPLE_PROMPTS.map((ex, i) => (
                                <button
                                    key={i}
                                    className="example-btn"
                                    onClick={() => handleExampleClick(ex)}
                                >
                                    {ex}
                                </button>
                            ))}
                        </div>
                    </div>
                )}

                {/* Loading */}
                {loading && (
                    <div className="loading-state">
                        <LoadingSpinner />
                        <p>AI đang phân tích yêu cầu...</p>
                    </div>
                )}

                {/* Error */}
                {error && (
                    <div className="error-msg">{error}</div>
                )}

                {/* Results */}
                {recommendations.length > 0 && (
                    <div className="results">
                        <h2>Kết quả ({recommendations.length} địa điểm)</h2>
                        <div className="results-grid">
                            {recommendations.map((rec, idx) => (
                                <div key={rec.id || idx} className="result-card">
                                    {rec.image_urls?.[0] && (
                                        <div className="result-image">
                                            <img
                                                src={rec.image_urls[0]}
                                                alt={rec.name}
                                                onError={(e) => e.target.src = 'https://via.placeholder.com/400x300?text=No+Image'}
                                            />
                                        </div>
                                    )}
                                    <div className="result-content">
                                        <h3>{rec.name}</h3>
                                        <p className="result-location">{rec.location_province}</p>

                                        {rec.justification_summary && (
                                            <p className="result-justification">
                                                {rec.justification_summary}
                                            </p>
                                        )}

                                        {rec.suggested_activities?.length > 0 && (
                                            <div className="result-activities">
                                                {rec.suggested_activities.slice(0, 3).map((a, i) => (
                                                    <span key={i} className="activity-tag">{a}</span>
                                                ))}
                                            </div>
                                        )}

                                        {rec.weather && (
                                            <p className="result-weather">
                                                {rec.weather.temp}°C - {rec.weather.description}
                                            </p>
                                        )}

                                        <Link to={`/destination/${rec.id}`} className="btn btn-secondary">
                                            Xem chi tiết
                                        </Link>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>
                )}

                {/* Empty State */}
                {!loading && status === 'empty' && (
                    <div className="empty-state">
                        <p>Không tìm thấy địa điểm phù hợp. Thử mô tả khác?</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default AIRecommendations;
