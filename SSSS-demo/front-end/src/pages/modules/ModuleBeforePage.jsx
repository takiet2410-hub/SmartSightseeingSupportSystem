import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axiosClient from '../../api/axiosClient';
import LoadingSpinner from '../../components/LoadingSpinner';

// --- COMPONENT: SEARCHABLE SELECT (CÓ MŨI TÊN) ---
const SearchableSelect = ({ options, value, onChange, placeholder }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [searchTerm, setSearchTerm] = useState("");
  const wrapperRef = useRef(null);

  // Đóng khi click ra ngoài
  useEffect(() => {
    const handleClickOutside = (event) => {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Sync value
  useEffect(() => {
    setSearchTerm(value || ""); // Nếu null/undefined thì về rỗng
  }, [value]);

  const filteredOptions = options.filter(opt => 
    opt.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const handleSelect = (opt) => {
    onChange(opt);
    setSearchTerm(opt);
    setIsOpen(false);
  };

  return (
    <div className="custom-select-container" ref={wrapperRef}>
      {/* Ô Input chính */}
      <input 
        className="searchable-input"
        placeholder={placeholder}
        value={searchTerm}
        onClick={() => setIsOpen(true)}
        onChange={(e) => {
            setSearchTerm(e.target.value);
            setIsOpen(true);
            onChange(e.target.value); 
        }}
      />
      
      {/* [NEW] Mũi tên chỉ xuống (Trang trí) */}
      <span className="input-arrow-icon">▼</span>
      
      {isOpen && (
        <div className="dropdown-list">
            {filteredOptions.length > 0 ? (
                filteredOptions.map((opt, idx) => (
                    <div 
                        key={idx} 
                        className="dropdown-item" 
                        onClick={() => handleSelect(opt)}
                    >
                        {opt}
                    </div>
                ))
            ) : (
                <div style={{padding:'15px', color:'#94a3b8', textAlign:'center'}}>Không tìm thấy</div>
            )}
        </div>
      )}
    </div>
  );
};

const ModuleBeforePage = () => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(false);
  const provinces = ['An Giang', 'Bà Rịa - Vũng Tàu', 'Bình Dương', 'Bình Phước', 'Bình Thuận', 'Bình Định', 'Bạc Liêu', 'Bắc Giang', 'Bắc Kạn', 'Bắc Ninh', 'Bến Tre', 'Cao Bằng', 'Cà Mau', 'Gia Lai', 'Hà Giang', 'Hà Nam', 'Hà Tĩnh', 'Hòa Bình', 'Hưng Yên', 'Hải Dương', 'Hậu Giang', 'Khánh Hòa', 'Kiên Giang', 'Kon Tum', 'Lai Châu', 'Long An', 'Lào Cai', 'Lâm Đồng', 'Lạng Sơn', 'Nam Định', 'Nghệ An', 'Ninh Bình', 'Ninh Thuận', 'Phú Thọ', 'Phú Yên', 'Quảng Bình', 'Quảng Nam', 'Quảng Ngãi', 'Quảng Ninh', 'Quảng Trị', 'Sóc Trăng', 'Sơn La', 'Thanh Hóa', 'Thành phố Cần Thơ', 'Thành phố Hà Nội', 'Thành phố Hải Phòng', 'Thành phố Hồ Chí Minh', 'Thành phố Đà Nẵng', 'Thái Bình', 'Thái Nguyên', 'Thừa Thiên Huế', 'Tiền Giang', 'Trà Vinh', 'Tuyên Quang', 'Tây Ninh', 'Vĩnh Long', 'Vĩnh Phúc', 'Yên Bái', 'Điện Biên', 'Đắk Lắk', 'Đắk Nông', 'Đồng Nai', 'Đồng Tháp'];

  // [FIX] STATE MẶC ĐỊNH LÀ RỖNG (KHÔNG CHỌN GÌ)
  const [formData, setFormData] = useState({
    currentLocation: '',
    availableTime: '', // Rỗng
    budget: '',        // Rỗng
    companion: '',     // Rỗng
    season: '',        // Rỗng
    vibe: ''
  });

  const handleInputChange = (e) => setFormData({ ...formData, [e.target.name]: e.target.value });
  
  // Xử lý riêng cho Location (Component con gọi lên)
  const handleLocationChange = (val) => setFormData({ ...formData, currentLocation: val });

  // Logic Toggle (Bấm chọn / Bấm lại để hủy)
  const handleToggle = (field, value) => {
    setFormData(prev => ({
        ...prev,
        [field]: prev[field] === value ? "" : value
    }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    // Validate: Phải có ít nhất 1 ràng buộc hoặc 1 sở thích
    const hasConstraints = formData.currentLocation || formData.availableTime || formData.budget || formData.companion || formData.season;
    const hasVibe = formData.vibe.trim().length > 0;

    if (!hasConstraints && !hasVibe) {
        return alert("Vui lòng chọn ít nhất một điều kiện lọc HOẶC nhập sở thích!");
    }
    
    setLoading(true);
    try {
      // Map dữ liệu sang chuẩn Backend
      let budgetCode = "";
      if (formData.budget) {
          if (formData.budget.includes("Thấp")) budgetCode = "thấp";
          else if (formData.budget.includes("Cao")) budgetCode = "cao";
          else budgetCode = "trung bình";
      }
      
      let timeCode = formData.availableTime ? formData.availableTime.replace("–", "-").toLowerCase() : "";

      const payload = {
        vibe_prompt: formData.vibe, 
        hard_constraints: { 
            location_province: formData.currentLocation,
            budget_range: budgetCode,
            available_time: timeCode,
            companion_tag: formData.companion.toLowerCase(),
            season_tag: formData.season.toLowerCase()
        }
      };
      
      const res = await axiosClient.post('/recommendations', payload);
      navigate('/recommend/results', { state: { data: res.data.recommendations, request: formData } });
    } catch (err) {
      alert("Lỗi kết nối Backend! (Đảm bảo Server 8000 đang chạy)");
      setLoading(false);
    }
  };

  const budgetOptions = ["Thấp (< 500k)", "Trung bình (500k – 2M)", "Cao (> 2M)"];
  const timeOptions = ["1–2 giờ", "2–4 giờ", "4–8 giờ", "8–24 giờ"];
  const companionOptions = ["Một mình", "Cặp đôi", "Gia đình", "Nhóm bạn bè"];
  const seasonOptions = ["Xuân", "Hạ", "Thu", "Đông", "Quanh năm"];

  return (
    <div className="form-page-container">
      {loading ? <LoadingSpinner message="AI đang tìm kiếm địa điểm phù hợp nhất..." /> : (
        <div className="form-card">
          <div className="form-header">
            <h2>Lên Kế Hoạch Chuyến Đi</h2>
            <p>Chọn các điều kiện lọc hoặc nhập sở thích để AI gợi ý.</p>
          </div>
          <form onSubmit={handleSubmit}>
            <div className="form-row">
              
              <div className="form-group">
                <label>📍 Địa điểm hiện tại (Tùy chọn)</label>
                {/* DROPDOWN SEARCHABLE */}
                <SearchableSelect 
                    options={provinces} 
                    value={formData.currentLocation}
                    onChange={handleLocationChange}
                    placeholder="Nhập tên hoặc chọn..."
                />
              </div>

              <div className="form-group">
                <label>🕒 Thời gian sẵn có</label>
                <div className="chip-group">
                    {timeOptions.map(opt => (
                        <div 
                            key={opt} 
                            className={`chip-label ${formData.availableTime === opt ? 'selected' : ''}`} 
                            onClick={() => handleToggle('availableTime', opt)}
                        >
                            {opt}
                        </div>
                    ))}
                </div>
              </div>
            </div>
            
            <div className="form-group"><label>💰 Ngân sách dự kiến</label><div className="chip-group">{budgetOptions.map(opt => (<div key={opt} className={`chip-label ${formData.budget === opt ? 'selected' : ''}`} onClick={() => handleToggle('budget', opt)}>{opt}</div>))}</div></div>
            <div className="form-group"><label>👥 Bạn đồng hành</label><div className="chip-group">{companionOptions.map(opt => (<div key={opt} className={`chip-label ${formData.companion === opt ? 'selected' : ''}`} onClick={() => handleToggle('companion', opt)}>{opt}</div>))}</div></div>
            <div className="form-group"><label>🌤️ Mùa du lịch</label><div className="chip-group">{seasonOptions.map(opt => (<div key={opt} className={`chip-label ${formData.season === opt ? 'selected' : ''}`} onClick={() => handleToggle('season', opt)}>{opt}</div>))}</div></div>
            
            <div className="form-group">
                <label>✨ Sở thích & Mong muốn (Tùy chọn)</label>
                <textarea className="textarea-field" name="vibe" rows="3" placeholder="Bạn muốn trải nghiệm gì? (Vd: Yên tĩnh, ngắm cảnh, ăn ngon...)" value={formData.vibe} onChange={handleInputChange}></textarea>
            </div>
            <button type="submit" className="btn-submit">TẠO KẾ HOẠCH</button>
          </form>
        </div>
      )}
    </div>
  );
};
export default ModuleBeforePage;