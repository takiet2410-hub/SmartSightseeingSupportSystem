import pandas as pd
import numpy as np
import os

# ================= CẤU HÌNH =================
# Tên file Excel đầu vào của bạn (để cùng thư mục hoặc đường dẫn tuyệt đối)
INPUT_FILE = "D:\sts\SmartSightseeingSupportSystem\data/destinations.xlsx" 

# Tên file Excel đầu ra (sau khi đã tính điểm)
OUTPUT_FILE = "filled_overall_rating.xlsx"

# Ngưỡng tin cậy (0.5 = Median - Top 50%, 0.25 = Top 75%)
# Nếu thấy điểm bị kéo xuống thấp quá, hãy giảm xuống 0.25 hoặc 0.1
M_QUANTILE = 0.25
# ============================================

def clean_google_data(df):
    """Làm sạch dữ liệu rating và review count"""
    print("--- Đang làm sạch dữ liệu ---")
    
    # 1. Xử lý Google Rating (Chuyển "4,5" -> 4.5)
    if 'google_rating' in df.columns:
        # Chuyển về chuỗi, thay dấu phẩy bằng dấu chấm
        df['google_rating'] = df['google_rating'].astype(str).str.replace(',', '.', regex=False)
        # Chuyển về số (gặp lỗi thì biến thành NaN -> 0)
        df['google_rating'] = pd.to_numeric(df['google_rating'], errors='coerce').fillna(0)
    else:
        print("❌ LỖI: Không tìm thấy cột 'google_rating'")
        return None

    # 2. Xử lý Google Review Count (Chuyển "1.000" hoặc "1,000" -> 1000)
    if 'google_review_count' in df.columns:
        # Xóa hết dấu chấm và dấu phẩy (vì đây là số nguyên đếm)
        df['google_review_count'] = df['google_review_count'].astype(str).str.replace('.', '', regex=False).str.replace(',', '', regex=False)
        # Chuyển về số
        df['google_review_count'] = pd.to_numeric(df['google_review_count'], errors='coerce').fillna(0)
    else:
        print("❌ LỖI: Không tìm thấy cột 'google_review_count'")
        return None
        
    return df

def calculate_weighted_rating(df):
    """Tính toán theo công thức IMDb"""
    print("--- Đang tính toán Weighted Rating ---")
    
    # 1. Tính C (Mean Vote toàn tập dữ liệu)
    # Chỉ tính trên những dòng có rating > 0 để tránh nhiễu
    valid_ratings = df[df['google_rating'] > 0]['google_rating']
    if len(valid_ratings) == 0:
        print("⚠️ Cảnh báo: Không có rating nào hợp lệ (>0). Dùng mặc định C=3.0")
        C = 3.0
    else:
        C = valid_ratings.mean()
        
    
    # 2. Tính m (Ngưỡng review tối thiểu)
    m = df['google_review_count'].quantile(M_QUANTILE)
    
    print(f"📊 THÔNG SỐ THỐNG KÊ:")
    print(f"   > Điểm trung bình toàn cục (C): {C:.2f} / 5.0")
    print(f"   > Ngưỡng review tối thiểu (m):  {m:.0f} lượt")
    print(f"   (Những địa điểm dưới {m:.0f} review sẽ bị kéo điểm về {C:.2f})")

    # 3. Áp dụng công thức
    v = df['google_review_count']
    R = df['google_rating']
    
    # Tránh chia cho 0
    denominator = v + m
    denominator = denominator.replace(0, 1) 
    
    # Ghi đè hoặc tạo mới cột overall_rating
    df['overall_rating'] = (v / denominator * R) + (m / denominator * C)
    
    # Làm tròn 2 chữ số
    df['overall_rating'] = df['overall_rating'].round(1)
    
    return df

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Không tìm thấy file: {INPUT_FILE}")
        print("Vui lòng sửa đường dẫn trong biến INPUT_FILE ở đầu code.")
        return

    print(f"📂 Đang đọc file: {INPUT_FILE} ...")
    try:
        df = pd.read_excel(INPUT_FILE)
    except Exception as e:
        print(f"❌ Lỗi đọc file Excel: {e}")
        return

    # Bước 1: Làm sạch
    df_clean = clean_google_data(df)
    if df_clean is None: return

    # Bước 2: Tính toán
    df_final = calculate_weighted_rating(df_clean)

    # Bước 3: Lưu file
    print(f"\n💾 Đang lưu file kết quả ra: {OUTPUT_FILE} ...")
    df_final.to_excel(OUTPUT_FILE, index=False)
    print("✅ HOÀN TẤT! Hãy dùng file mới này để chạy ingest_data.py")

if __name__ == "__main__":
    main()