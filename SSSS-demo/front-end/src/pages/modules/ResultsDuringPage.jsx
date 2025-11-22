import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const ResultsDuringPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const result = location.state?.data || {};
  React.useEffect(() => {
    if (!result) {
        alert("Vui lòng upload ảnh để nhận diện!");
        navigate('/identify');
    }
  }, [result, navigate]);

  if (!result) return null;

  return (
    <div className="form-page-container">
      <div className="form-card" style={{maxWidth:'1000px'}}>
        <button onClick={() => navigate('/identify')} style={{background:'none', border:'none', color:'white', marginBottom:'1rem', cursor:'pointer', fontSize:'1.1rem'}}>← Quét Lại</button>
        <div style={{display:'flex', gap:'3rem', flexWrap:'wrap'}}>
            <div style={{flex:1, position:'relative'}}>
                <img src="https://images.unsplash.com/photo-1545133233-5cb50ce88645?q=80&w=800" style={{width:'100%', borderRadius:'16px', boxShadow:'0 10px 30px rgba(0,0,0,0.3)'}} />
                <span style={{position:'absolute', bottom:'15px', right:'15px', background:'#22c55e', color:'white', padding:'5px 12px', borderRadius:'8px', fontWeight:'bold'}}>
                    Độ tin cậy: {(result.confidence*100).toFixed(0)}%
                </span>
            </div>
            <div style={{flex:1}}>
                <h2 style={{fontFamily:'Merriweather', fontSize:'2.2rem', color:'var(--accent)', marginBottom:'0.5rem'}}>{result.name}</h2>
                <p style={{color:'#94a3b8', marginBottom:'1.5rem'}}>⭐ Đánh giá: {result.details?.ratings || "4.5/5"}</p>
                
                <div style={{background:'rgba(255,255,255,0.05)', padding:'1.5rem', borderRadius:'12px', marginBottom:'2rem', border:'1px solid rgba(255,255,255,0.1)'}}>
                    <h4 style={{color:'var(--primary)', marginBottom:'0.5rem', textTransform:'uppercase', fontSize:'0.9rem'}}>Thông Tin Tóm Tắt</h4>
                    <p style={{lineHeight:'1.6', color:'#e2e8f0'}}>{result.summary}</p>
                    <div style={{marginTop:'1rem', borderTop:'1px solid rgba(255,255,255,0.1)', paddingTop:'1rem'}}>
                        <p>🕒 <b>Giờ mở cửa:</b> {result.details?.hours}</p>
                        <p style={{marginTop:'5px'}}>💵 <b>Giá vé:</b> {result.details?.fee}</p>
                    </div>
                </div>

                <div style={{display:'flex', gap:'1rem'}}>
                    <button className="btn-submit" style={{marginTop:0, flex:1, fontSize:'1rem'}}>📖 Xem Thêm</button>
                    <button className="btn-submit" style={{marginTop:0, background:'#334155', flex:1, fontSize:'1rem'}}>📍 Tìm Quanh Đây</button>
                </div>
            </div>
        </div>
      </div>
    </div>
  );
};
export default ResultsDuringPage;