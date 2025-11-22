import React from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

const ResultsAfterPage = () => {
  const location = useLocation();
  const navigate = useNavigate();
  const result = location.state?.data || {};
  React.useEffect(() => {
    if (!result) {
        alert("Chưa có album nào được tạo! Vui lòng upload ảnh.");
        navigate('/curate');
    }
  }, [result, navigate]);

  if (!result) return null;

  return (
    <div className="results-container" style={{padding:'2rem 4rem'}}>
      <div className="results-header">
        <button className="btn-back" onClick={() => navigate('/curate')}>← Tạo Album Mới</button>
        <h2 style={{fontFamily:'Merriweather', fontSize:'2.5rem', color:'white'}}>Câu Chuyện Của Bạn</h2>
        <div></div>
      </div>
      <div style={{display:'grid', gridTemplateColumns:'2fr 1fr', gap:'2rem', maxWidth:'1200px', margin:'0 auto'}}>
        {/* Cột Trái */}
        <div style={{display:'flex', flexDirection:'column', gap:'1.5rem'}}>
            <div style={{background:'#1e293b', padding:'2rem', borderRadius:'16px', border:'1px solid #334155'}}>
                <h3 style={{color:'var(--primary)', fontSize:'1.8rem', marginBottom:'0.5rem', fontFamily:'Merriweather'}}>{result.trip_summary}</h3>
                <p style={{color:'#94a3b8'}}>Tổng số ảnh: {result.total_photos} • Được tạo bởi AI</p>
            </div>

            {result.clusters?.map((c, i) => (
                <div key={i} style={{background:'rgba(255,255,255,0.03)', borderRadius:'16px', border:'1px solid rgba(255,255,255,0.1)', display:'flex', padding:'1.5rem', alignItems:'center', gap:'1.5rem'}}>
                    <div style={{fontSize:'2.5rem', background:'#334155', width:'80px', height:'80px', display:'flex', alignItems:'center', justifyContent:'center', borderRadius:'12px'}}>🖼️</div>
                    <div>
                        <span style={{background:'var(--accent)', color:'black', padding:'3px 8px', borderRadius:'4px', fontSize:'0.75rem', fontWeight:'bold', textTransform:'uppercase'}}>Cụm #{i+1}</span>
                        <h3 style={{margin:'0.5rem 0', color:'white'}}>{c.title}</h3>
                        <p style={{color:'#94a3b8', fontSize:'0.95rem'}}>{c.description}</p>
                        <p style={{marginTop:'0.5rem', fontWeight:'bold', color:'var(--primary)', fontSize:'0.9rem'}}>{c.photo_count} ảnh được chọn</p>
                    </div>
                </div>
            ))}
        </div>

        {/* Cột Phải */}
        <div style={{display:'flex', flexDirection:'column', gap:'2rem'}}>
            <div style={{background:'#1e293b', borderRadius:'16px', padding:'2rem', border:'1px solid #334155'}}>
                <h4 style={{color:'white', marginBottom:'1rem', fontFamily:'Merriweather'}}>🗺️ Bản Đồ Hành Trình</h4>
                <div style={{height:'200px', background:'#0f172a', borderRadius:'8px', display:'flex', alignItems:'center', justifyContent:'center', color:'#64748b', border:'1px dashed #334155'}}>[Map Placeholder]</div>
            </div>

            <div style={{background:'rgba(255,255,255,0.05)', padding:'2rem', borderRadius:'16px', border:'1px solid rgba(255,255,255,0.1)'}}>
                <h4 style={{marginBottom:'1.5rem', color:'white'}}>Xuất & Chia Sẻ</h4>
                <button className="btn-submit" style={{marginBottom:'1rem', fontSize:'1rem'}}>📤 Xuất file PDF</button>
                <button className="btn-submit" style={{background:'#1da1f2', fontSize:'1rem'}}>🔗 Sao chép Link</button>
            </div>
        </div>
      </div>
    </div>
  );
};
export default ResultsAfterPage;