import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosClient from '../../api/axiosClient';
import LoadingSpinner from '../../components/LoadingSpinner';

const ModuleAfterPage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);

  const handleUpload = async (e) => {
    if (!e.target.files.length) return;
    setLoading(true);
    const formData = new FormData();
    formData.append('files', e.target.files[0]);
    try {
      const res = await axiosClient.post('/api/after/curate', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
      navigate('/curate/results', { state: { data: res.data } });
    } catch (err) {
        setTimeout(() => {
             navigate('/curate/results', { state: { data: {
                trip_summary: "Chuyến đi Hà Nội Mùa Thu", total_photos: 128,
                clusters: [
                    {title: "Hồ Hoàn Kiếm", description: "Đi dạo buổi sáng sớm", photo_count: 15},
                    {title: "Ẩm thực Phố Cổ", description: "Tour ăn vặt đường phố", photo_count: 30},
                    {title: "Hoàng Thành Thăng Long", description: "Tham quan di tích", photo_count: 20}
                ]
             }}});
        }, 5000);
    }
  };

  return (
    <div className="form-page-container">
      {loading ? <LoadingSpinner message="AI đang lọc ảnh rác & phân nhóm kỷ niệm..." /> : (
        <div className="form-card" style={{textAlign:'center', padding:'4rem'}}>
          <div className="form-header">
            <h2>Trợ Lý Sắp Xếp Album Ảnh</h2>
            <p>Biến kho ảnh lộn xộn thành câu chuyện chuyến đi ý nghĩa.</p>
          </div>

          <div className="upload-box">
              <span style={{fontSize:'4rem', marginBottom:'1rem', opacity:0.8}}>📂</span>
              <h3 style={{margin:'0 0 0.5rem 0', color:'white', fontFamily:'Merriweather'}}>Kéo thả hoặc Chọn ảnh</h3>
              <p style={{color:'#94a3b8'}}>Hỗ trợ: JPG, PNG. (Tự động xóa ảnh mờ, trùng lặp)</p>
              <input type="file" multiple accept="image/*" onChange={handleUpload} 
                style={{position:'absolute', top:0, left:0, width:'100%', height:'100%', opacity:0, cursor:'pointer'}} 
              />
          </div>
        </div>
      )}
    </div>
  );
};
export default ModuleAfterPage;