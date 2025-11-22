import React, { useState, useEffect } from 'react';

const PlaceModal = ({ place, onClose }) => {
  if (!place) return null;
  
  const images = (place.image_urls && place.image_urls.length > 0) 
    ? place.image_urls 
    : ['https://images.unsplash.com/photo-1500382017468-9049fed747ef?q=80&w=1200'];

  const [currentIndex, setCurrentIndex] = useState(0);

  useEffect(() => {
    if (images.length > 1) {
        const timer = setInterval(() => {
            setCurrentIndex((prev) => (prev + 1) % images.length);
        }, 3500);
        return () => clearInterval(timer);
    }
  }, [images.length]);

  const nextImage = (e) => { e.stopPropagation(); setCurrentIndex((prev) => (prev + 1) % images.length); };
  const prevImage = (e) => { e.stopPropagation(); setCurrentIndex((prev) => (prev - 1 + images.length) % images.length); };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={e => e.stopPropagation()}>
        {/* Nút Đóng */}
        <button className="modal-close-btn" onClick={onClose}>×</button>
        
        {/* Carousel Ảnh */}
        <div className="modal-carousel-container">
             <img src={images[currentIndex]} className="modal-carousel-img" alt={place.name} key={currentIndex} />
             <div className="modal-carousel-overlay"></div>
             
             {images.length > 1 && (
                <>
                    <button className="carousel-btn prev" onClick={prevImage}>❮</button>
                    <button className="carousel-btn next" onClick={nextImage}>❯</button>
                    <div className="carousel-dots">
                        {images.map((_, idx) => (
                            <div key={idx} className={`carousel-dot ${idx === currentIndex ? 'active' : ''}`} onClick={() => setCurrentIndex(idx)}></div>
                        ))}
                    </div>
                </>
             )}
        </div>
        
        <div className="modal-body">
          {/* 1. Header Info */}
          <div style={{display:'flex', justifyContent:'space-between', alignItems:'flex-start', marginBottom:'1.5rem'}}>
             <div>
                <h2 style={{fontFamily:'Merriweather', fontSize:'2.5rem', color:'var(--accent)', marginBottom:'0.5rem'}}>{place.name}</h2>
                <p style={{fontSize:'1.1rem', color:'#94a3b8'}}>📍 {place.specific_address || place.location_province}</p>
             </div>
             <div style={{textAlign:'right'}}>
                <span style={{fontSize:'1.8rem', fontWeight:'bold', color:'#fbbf24'}}>⭐ {place.overall_rating}</span>
             </div>
          </div>

          {/* 2. Weather Widget */}
          {place.weather && (
              <div style={{display:'inline-flex', alignItems:'center', gap:'15px', background:'rgba(6, 182, 212, 0.1)', padding:'10px 20px', borderRadius:'12px', border:'1px solid var(--accent)', marginBottom:'2rem'}}>
                  <img src={`http://openweathermap.org/img/wn/${place.weather.icon}.png`} alt="weather" width="50" />
                  <div>
                      <p style={{fontWeight:'bold', fontSize:'1.4rem', margin:0, color:'white'}}>{place.weather.temp}°C</p>
                      <p style={{margin:0, fontSize:'0.95rem', color:'#cbd5e1'}}>{place.weather.description}</p>
                  </div>
              </div>
          )}
          
          {/* 3. [NEW] AI Justification Summary (Thêm vào đây) */}
          {place.justification_summary && (
              <div className="ai-reason-box">
                  <h4 style={{color:'var(--primary)', margin:'0 0 0.5rem 0', fontSize:'1rem', textTransform:'uppercase', display:'flex', alignItems:'center', gap:'8px'}}>
                     🤖 Tại sao AI đề xuất nơi này?
                  </h4>
                  <p style={{fontSize:'1.1rem', lineHeight:'1.6', color:'#f1f5f9', margin:0, fontStyle:'italic'}}>
                      "{place.justification_summary}"
                  </p>
              </div>
          )}

          {/* 4. Detail Grid (Đã đổi thứ tự: Activities lên trên, Description xuống dưới) */}
          <div className="detail-grid">
            
            {/* KHUNG 1: TRẢI NGHIỆM NỔI BẬT (Activities - Lên trên) */}
            <div className="detail-box" style={{borderColor:'var(--accent)'}}>
               <div className="detail-section-title" style={{color:'var(--accent)', fontSize: '1.2rem'}}>✨ Trải nghiệm không thể bỏ qua</div>
               {place.suggested_activities && place.suggested_activities.length > 0 ? (
                   <ul style={{paddingLeft:'20px', marginTop:'10px', color:'#e2e8f0'}}>
                      {place.suggested_activities.map((act, i) => (
                          <li key={i} style={{marginBottom:'8px', fontSize:'1.05rem'}}>{act}</li>
                      ))}
                   </ul>
               ) : (
                   <p style={{color:'#94a3b8', marginTop:'10px'}}>Đang cập nhật hoạt động...</p>
               )}
            </div>

            {/* KHUNG 2: GIỚI THIỆU CHI TIẾT (Description - Xuống dưới) */}
            <div className="detail-box">
               <div className="detail-section-title" style={{color:'white', fontSize: '1.2rem'}}>📖 Giới thiệu</div>
               <p style={{fontSize:'1.05rem', lineHeight:'1.8', color:'#cbd5e1', marginTop:'10px', textAlign:'justify'}}>
                  {place.description || "Thông tin đang được cập nhật."}
               </p>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
};
export default PlaceModal;