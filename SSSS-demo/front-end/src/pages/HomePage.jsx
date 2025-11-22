import React from 'react';
import { Link } from 'react-router-dom';

const HomePage = () => {
  const images = [
    'https://www.vietnambooking.com/wp-content/uploads/2018/12/doc-mien-dat-nuoc-chiem-nguong-canh-dep-viet-nam-19122018-3.jpg',
    'https://cellphones.com.vn/sforum/wp-content/uploads/2023/10/canh-dep-3.jpg',
    'https://images.unsplash.com/photo-1559592413-7cec4d0cae2b?q=80&w=1200'
  ];

  const quotes = [
    { text: "Đích đến của chúng ta không phải là một vùng đất, mà là một cách nhìn mới.", author: "Henry Miller" },
    { text: "Thế giới là một cuốn sách, ai không đi chỉ đọc một trang.", author: "Saint Augustine" },
    { text: "Hãy ngắm nhìn thế giới. Điều đó tuyệt vời hơn bất cứ giấc mơ nào.", author: "Ray Bradbury" }
  ];

  return (
    <div style={{display:'flex', flexDirection:'column'}}>
      {/* HERO SECTION */}
      <div className="homepage-hero-section">
        <div className="hero-left">
          <div className="hero-image-carousel">
            {images.map((img, index) => (
              <img key={index} src={img} alt="Vietnam Travel" style={{ animationDelay: `${index * 5}s` }} />
            ))}
          </div>
        </div>
        <div className="hero-right">
          <h1 className="hero-title">Đồng Hành<br/><span>Cùng Bạn Trên Mọi Chặng Đường.</span></h1>
          <div className="quote-carousel-container">
            {quotes.map((q, index) => (
              <div key={index} className="quote-item" style={{ animationDelay: `${index * 5}s` }}>
                <p className="quote-text">"{q.text}"</p>
                <span className="quote-author">— {q.author}</span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* MODULES SECTION */}
      <div className="modules-section-homepage">
        <h2>Chọn Công Cụ Của Bạn</h2>
        <div className="homepage-modules-grid">
          <Link to="/recommend" className="module-card-homepage">
            <span className="icon">🧭</span>
            <h3>AI Travel Consultant</h3>
            <p>Lên kế hoạch, gợi ý điểm đến thông minh dựa trên ngân sách và sở thích cá nhân.</p>
            <span className="cta">Lập Kế Hoạch →</span>
          </Link>
          <Link to="/identify" className="module-card-homepage">
            <span className="icon">📸</span>
            <h3>Landmark Identification</h3>
            <p>Quét ảnh để nhận diện địa danh lịch sử và tra cứu thông tin tức thì.</p>
            <span className="cta">Nhận Diện →</span>
          </Link>
          <Link to="/curate" className="module-card-homepage">
            <span className="icon">🖼️</span>
            <h3>AI Album Curator</h3>
            <p>Tự động lọc ảnh rác, sắp xếp kỷ niệm thành album câu chuyện ý nghĩa.</p>
            <span className="cta">Tạo Album →</span>
          </Link>
        </div>
      </div>
    </div>
  );
};
export default HomePage;