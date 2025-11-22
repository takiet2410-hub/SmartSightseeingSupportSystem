import os

# ==============================================================================
# RESULTS PAGE (SẠCH - KHÔNG CÒN MOCK DATA)
# ==============================================================================
results_before_jsx = """
import React, { useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import PlaceModal from '../../components/PlaceModal';

const ResultsBeforePage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  
  // Lấy dữ liệu trực tiếp từ Backend gửi sang
  // Nếu không có data, mặc định là mảng rỗng []
  const results = location.state?.data || [];
  const [selected, setSelected] = useState(null);

  // Hàm hiển thị ảnh an toàn (Chỉ giữ lại logic ảnh default nếu link lỗi/thiếu)
  const getValidImage = (place) => {
    if (place.image_urls && place.image_urls.length > 0) return place.image_urls[0];
    // Ảnh placeholder đẹp nếu không có ảnh
    return "https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=1200"; 
  };

  return (
    <div className="results-container" style={{padding: '4rem'}}>
      <div className="results-header">
        <button className="btn-back" onClick={() => navigate('/recommend')}>
            <span>←</span> Chỉnh sửa kế hoạch
        </button>
        <h2 style={{fontFamily:'Merriweather', fontSize:'2.2rem', color: 'white', margin:0, textAlign:'center', flex:1}}>
            Gợi Ý Tốt Nhất Cho Bạn
        </h2>
        <div style={{width:'180px'}}></div>
      </div>

      {/* Kiểm tra nếu có kết quả thì hiển thị, không thì báo lỗi */}
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
                        onError={(e) => e.target.src = "https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=1200"}
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
        <div style={{textAlign: 'center', marginTop: '5rem', color: '#94a3b8'}}>
            <h3 style={{fontSize: '2rem', marginBottom: '1rem'}}>😕 Không tìm thấy địa điểm nào</h3>
            <p>Backend chưa trả về dữ liệu hoặc không có địa điểm phù hợp với bộ lọc.</p>
            <button 
                onClick={() => navigate('/recommend')}
                style={{
                    marginTop: '2rem', padding: '10px 25px', 
                    background: 'var(--primary)', border: 'none', 
                    color: 'white', borderRadius: '50px', cursor: 'pointer', fontWeight: 'bold'
                }}
            >
                Thử lại ngay
            </button>
        </div>
      )}
      
      <PlaceModal place={selected} onClose={() => setSelected(null)} />
    </div>
  );
};
export default ResultsBeforePage;
"""

# --- GHI FILE ---
def remove_mock():
    path = "src/pages/modules/ResultsBeforePage.jsx"
    with open(path, 'w', encoding='utf-8') as f:
        f.write(results_before_jsx.strip())
    print(f"✅ Updated: {path} (MOCK DATA REMOVED)")

if __name__ == "__main__":
    remove_mock()
    print("\\n✨ Xong! Bây giờ Frontend hoàn toàn phụ thuộc vào Backend.")