import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosClient from '../../api/axiosClient';
import LoadingSpinner from '../../components/LoadingSpinner';

const ModuleDuringPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleScan = async (e) => {
    const file = e.target.files[0];
    if (!file) return;
    
    // Xin quyền GPS
    if ("geolocation" in navigator) {
        navigator.geolocation.getCurrentPosition(() => {}, () => alert("Cảnh báo: Không lấy được vị trí GPS. Kết quả có thể kém chính xác hơn."));
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const res = await axiosClient.post('/api/during/identify', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      navigate('/identify/results', { state: { data: res.data.result } });
    } catch (err) {
        // Mock fallback
        setTimeout(() => {
            navigate('/identify/results', { state: { data: {
                name: "Nhà thờ Đức Bà", confidence: 0.98, summary: "Biểu tượng kiến trúc Pháp cổ kính giữa lòng Sài Gòn, được xây dựng bằng gạch đỏ Marseille.",
                details: { hours: "8:00 - 11:00, 14:00 - 16:00", fee: "Miễn phí tham quan", ratings: "4.7/5" }
            }}});
        }, 2000);
    }
  };

  return (
    <div className="form-page-container">
      {loading ? <LoadingSpinner message="AI đang phân tích đặc điểm kiến trúc..." /> : (
        <div className="form-card" style={{textAlign:'center', padding:'4rem'}}>
          <div className="form-header">
            <h2>Tra Cứu Địa Danh Tức Thì</h2>
            <p>Hướng camera về phía địa danh để nhận thông tin lịch sử & văn hóa.</p>
          </div>
          
          <div className="upload-box">
             <span style={{fontSize:'5rem', marginBottom:'1rem', opacity:0.8}}>📸</span>
             <p style={{color:'#cbd5e1', fontSize:'1.2rem'}}>Chạm để Mở Camera / Tải Ảnh</p>
             <input type="file" accept="image/*" onChange={handleScan} 
                style={{position:'absolute', top:0, left:0, width:'100%', height:'100%', opacity:0, cursor:'pointer'}} 
             />
          </div>
          
          <p style={{color:'rgba(255,255,255,0.5)', fontSize:'0.9rem'}}>💡 Mẹo: Đứng đối diện chính diện công trình để có kết quả tốt nhất.</p>
        </div>
      )}
    </div>
  );
};
export default ModuleDuringPage;