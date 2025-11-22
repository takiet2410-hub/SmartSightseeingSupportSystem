import os

# ==============================================================================
# 1. CSS CẬP NHẬT (THÊM MŨI TÊN VÀO Ô SEARCH)
# ==============================================================================
css_patch = """
/* --- [FINAL FIX] DROPDOWN STYLE --- */

/* Container cho ô tìm kiếm */
.custom-select-container {
  position: relative;
  width: 100%;
}

/* Ô nhập liệu (Input) - Thêm padding bên phải để tránh đè mũi tên */
.searchable-input {
  width: 100%; 
  padding: 16px 45px 16px 20px; /* Padding phải 45px chừa chỗ cho mũi tên */
  
  /* Nền tối và viền sáng rõ ràng */
  background: rgba(255, 255, 255, 0.05) !important; 
  border: 1px solid rgba(255, 255, 255, 0.3) !important; 
  
  border-radius: 12px !important;
  color: #ffffff !important; 
  font-weight: 500;
  font-size: 1rem; 
  font-family: 'Roboto', sans-serif;
  outline: none; 
  transition: all 0.3s ease;
  cursor: text;
}

/* Khi bấm vào (Focus) */
.searchable-input:focus { 
  border-color: var(--accent) !important; 
  background: rgba(255, 255, 255, 0.1) !important; 
  box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.25) !important;
}

/* Mũi tên chỉ xuống (▼) */
.input-arrow-icon {
  position: absolute;
  right: 15px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--accent);
  font-size: 0.8rem;
  pointer-events: none; /* Để click xuyên qua vào input */
  transition: transform 0.3s;
}

/* Xoay mũi tên khi menu mở (Thêm class 'open' bằng JS nếu muốn, ở đây để tĩnh) */
.custom-select-container:focus-within .input-arrow-icon {
  transform: translateY(-50%) rotate(180deg);
  color: var(--primary);
}

/* Danh sách xổ xuống */
.dropdown-list {
    position: absolute;
    top: 115%; left: 0; width: 100%;
    max-height: 280px; overflow-y: auto;
    background: #1e293b !important;
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 12px;
    z-index: 1000;
    box-shadow: 0 10px 40px rgba(0,0,0,0.5);
}

.dropdown-item {
    padding: 14px 20px;
    color: #e2e8f0;
    border-bottom: 1px solid rgba(255,255,255,0.05);
    cursor: pointer;
    transition: 0.2s;
}
.dropdown-item:hover {
    background: var(--primary);
    color: white;
    padding-left: 25px;
}
"""

# ==============================================================================
# 2. REACT CODE (STATE MẶC ĐỊNH LÀ RỖNG)
# ==============================================================================
vietnam_provinces = [
    "An Giang", "Bà Rịa - Vũng Tàu", "Bạc Liêu", "Bắc Giang", "Bắc Kạn", "Bắc Ninh", 
    "Bến Tre", "Bình Dương", "Bình Định", "Bình Phước", "Bình Thuận", "Cà Mau", 
    "Cao Bằng", "Đắk Lắk", "Đắk Nông", "Điện Biên", "Đồng Nai", "Đồng Tháp", 
    "Gia Lai", "Hà Giang", "Hà Nam", "Hà Tĩnh", "Hải Dương", "Hậu Giang", 
    "Hòa Bình", "Hưng Yên", "Khánh Hòa", "Kiên Giang", "Kon Tum", "Lai Châu", 
    "Lạng Sơn", "Lào Cai", "Lâm Đồng", "Long An", "Nam Định", "Nghệ An", 
    "Ninh Bình", "Ninh Thuận", "Phú Thọ", "Phú Yên", "Quảng Bình", "Quảng Nam", 
    "Quảng Ngãi", "Quảng Ninh", "Quảng Trị", "Sóc Trăng", "Sơn La", "Tây Ninh", 
    "Thái Bình", "Thái Nguyên", "Thanh Hóa", "Thừa Thiên Huế", "Tiền Giang", 
    "Trà Vinh", "Tuyên Quang", "Vĩnh Long", "Vĩnh Phúc", "Yên Bái",
    "Thành phố Cần Thơ", "Thành phố Đà Nẵng", "Thành phố Hà Nội", "Thành phố Hải Phòng", "Thành phố Hồ Chí Minh"
]
vietnam_provinces.sort()

module_before_template = """
import React, { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
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
  const provinces = __PROVINCES_LIST__;

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
      
      const res = await axios.post('http://127.0.0.1:8000/recommendations', payload);
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
"""
module_before_content = module_before_template.replace("__PROVINCES_LIST__", str(vietnam_provinces))

# --- GHI FILE ---
def fix_dropdown_final():
    # 1. CSS (Thêm vào cuối file)
    with open("src/App.css", 'a', encoding='utf-8') as f:
        f.write("\n" + css_patch)
    print("✅ CSS Updated: Added Arrow & Fixed Border")

    # 2. React
    with open("src/pages/modules/ModuleBeforePage.jsx", 'w', encoding='utf-8') as f:
        f.write(module_before_content.strip())
    print("✅ React Updated: Default Empty State & UI Logic")

if __name__ == "__main__":
    fix_dropdown_final()
    print("\\n✨ DONE! Khung nhập liệu giờ đã có mũi tên và mặc định không chọn gì.")