import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import PlaceModal from '../../components/PlaceModal';

const ResultsBeforePage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Lấy dữ liệu trực tiếp từ Backend gửi sang
  const incomingData = location.state?.data;
  const [results, setResults] = useState(Array.isArray(incomingData) ? incomingData : []);
  const [selected, setSelected] = useState(null);
  useEffect(() => {
    if (incomingData) {
        setResults(Array.isArray(incomingData) ? incomingData : []);
    } else {
        // Nếu không có dữ liệu, đợi 1 xíu rồi đá về trang form
        alert("Không tìm thấy dữ liệu chuyến đi! Vui lòng lập kế hoạch lại.");
        navigate('/recommend');
    }
  }, [incomingData, navigate]);

  // Nếu chưa có data (đang redirect), return null để không render lỗi
  if (!incomingData && results.length === 0) return null;
  
  // Hàm hiển thị ảnh an toàn
  const getValidImage = (place) => {
    if (place.image_urls && place.image_urls.length > 0) return place.image_urls[0];
    return "https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=1200"; 
  };

  return (
    <div className="results-container" style={{padding: '4rem'}}>
      <div className="results-header">
        <button className="btn-back" onClick={() => navigate('/recommend')}>
            <span>←</span> Chỉnh sửa kế hoạch
        </button>
        <h2 style={{fontFamily:'Merriweather', fontSize:'2.2rem', color: 'white', margin:0, textAlign:'center', flex:1}}>
            Kết Quả Gợi Ý
        </h2>
        <div style={{width:'180px'}}></div>
      </div>

      {/* KIỂM TRA: Nếu có kết quả thì hiện lưới, không thì báo lỗi */}
      {results.length > 0 ? (
        <div className="results-grid">
            {results.map((place, i) => (
            <div key={i} className="travel-card" onClick={() => setSelected(place)}>
                <div className="card-img-wrapper">
                    <span className="rank-tag">Top #{place.rank || i + 1}</span>
                    <div className="rating-badge">⭐ {place.overall_rating || 4.5}/5</div>
                    <img 
                        src={getValidImage(place)} 
                        className="card-img" 
                        alt={place.name} 
                    />
                </div>
                <div className="travel-card-body">
                    <h3 className="card-title">{place.name}</h3>
                    <div className="location">📍 {place.location_province}</div>
                    <p className="desc">
                        {place.justification_summary || place.description}
                    </p>
                    <div className="card-footer">
                        <span className="view-btn">Xem Chi Tiết →</span>
                    </div>
                </div>
            </div>
            ))}
        </div>
      ) : (
        <div style={{textAlign: 'center', marginTop: '4rem', color: '#94a3b8', background: 'rgba(255,255,255,0.05)', padding: '3rem', borderRadius: '20px'}}>
            <span style={{fontSize: '4rem', display: 'block', marginBottom: '1rem'}}>🤔</span>
            <h3 style={{fontSize: '1.8rem', color: 'white', marginBottom: '0.5rem'}}>Chưa tìm thấy địa điểm phù hợp</h3>
            <p style={{fontSize: '1.1rem'}}>Có thể do Backend chưa trả về dữ liệu hoặc bộ lọc quá chặt.</p>
            <p style={{fontSize: '0.9rem', marginTop: '0.5rem', color: '#f43f5e'}}>Vui lòng kiểm tra lại Terminal Backend (Server) để xem lỗi chi tiết.</p>
        </div>
      )}
      
      <PlaceModal place={selected} onClose={() => setSelected(null)} />
    </div>
  );
};
export default ResultsBeforePage;