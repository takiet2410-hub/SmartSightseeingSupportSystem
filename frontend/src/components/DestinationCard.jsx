import React from 'react';
import { Link } from 'react-router-dom';
import './DestinationCard.css';

const DestinationCard = ({ destination }) => {
    const { id, name, location_province, image_urls, overall_rating } = destination;

    // Get first image or use placeholder
    const imageUrl = image_urls && image_urls.length > 0
        ? image_urls[0]
        : 'https://via.placeholder.com/400x300?text=No+Image';

    // Render star rating
    const renderStars = (rating) => {
        const stars = [];
        const fullStars = Math.floor(rating);
        const hasHalfStar = rating % 1 >= 0.5;

        for (let i = 0; i < 5; i++) {
            if (i < fullStars) {
                stars.push(<span key={i} className="star filled">★</span>);
            } else if (i === fullStars && hasHalfStar) {
                stars.push(<span key={i} className="star half">★</span>);
            } else {
                stars.push(<span key={i} className="star">☆</span>);
            }
        }
        return stars;
    };

    return (
        <Link to={`/destination/${id}`} className="destination-card">
            <div className="card-image-wrapper">
                <img
                    src={imageUrl}
                    alt={name}
                    className="card-image"
                    loading="lazy"
                    onError={(e) => {
                        e.target.src = 'https://via.placeholder.com/400x300?text=Image+Not+Found';
                    }}
                />
                <div className="card-overlay"></div>
            </div>

            <div className="card-content">
                <h3 className="card-title">{name}</h3>

                <div className="card-location">
                    <span className="location-icon">📍</span>
                    <span className="location-text">{location_province}</span>
                </div>

                <div className="card-rating">
                    <div className="stars">
                        {renderStars(overall_rating)}
                    </div>
                    <span className="rating-value">{overall_rating.toFixed(1)}</span>
                </div>
            </div>
        </Link>
    );
};

export default DestinationCard;
