import sys
import os

# Thêm đường dẫn hiện tại vào path để import được modules
sys.path.append(os.getcwd())

try:
    from modules.vectorizer import HybridVectorizer
    
    print("⏳ Đang khởi tạo và kiểm tra Vectorizer...")
    
    # 1. Khởi tạo
    vectorizer = HybridVectorizer()
    
    # 2. Fit dữ liệu giả (Vì Hybrid thường cần fit TF-IDF/BM25 trước)
    dummy_corpus = [
        "Kiểm tra số chiều vector.",
        "Đây là dữ liệu mẫu để vectorizer học từ vựng."
    ]
    if hasattr(vectorizer, 'fit'):
        vectorizer.fit(dummy_corpus)

    # 3. Tạo vector thử
    test_vector = vectorizer.transform_single("Test dimension")
    
    # 4. In kết quả
    print("\n" + "="*40)
    print(f"✅ KẾT QUẢ: Số chiều vector (numDimensions) là: {len(test_vector)}")
    print("="*40 + "\n")
    
    # Gợi ý cấu hình cho Atlas
    print(f"👉 Hãy điền số {len(test_vector)} vào trường 'numDimensions' trong Atlas Index.")

except ImportError:
    print("❌ Lỗi: Không tìm thấy file 'modules/vectorizer.py'.\nHãy chắc chắn bạn lưu file này ở thư mục gốc dự án (cùng cấp với folder 'modules').")
except Exception as e:
    print(f"❌ Có lỗi xảy ra: {e}")