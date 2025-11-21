import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
import os

# --- CẤU HÌNH ---
MODEL_PATH = 'junk_filter_model_v3.h5'
TEST_IMAGE_PATH = r's12.jpg' # <--- THAY ĐƯỜNG DẪN ẢNH Ở ĐÂY
IMG_SIZE = (224, 224)

# --- 1. TẢI MÔ HÌNH ---
print("⏳ Đang tải mô hình...")
try:
    model = tf.keras.models.load_model(MODEL_PATH)
    print("✅ Đã tải mô hình thành công!")
except:
    print("❌ Không tìm thấy file model. Hãy kiểm tra lại tên file.")
    exit()

def predict_single_image():
    # --- 2. XỬ LÝ ẢNH ĐẦU VÀO ---
    # Quy trình này PHẢI GIỐNG HỆT lúc train (Resize -> Array -> Normalize)
    try:
        img = image.load_img(TEST_IMAGE_PATH, target_size=IMG_SIZE)
        img_array = image.img_to_array(img)
        img_array = img_array / 255.0  # Chuẩn hóa về 0-1
        
        # Thêm chiều batch (Model cần input 4 chiều: 1, 224, 224, 3)
        img_array = np.expand_dims(img_array, axis=0)

        # --- 3. DỰ ĐOÁN ---
        prediction = model.predict(img_array)
        score = prediction[0][0] # Lấy con số xác suất (từ 0 đến 1)

        # --- 4. ĐỌC KẾT QUẢ ---
        # Lưu ý: Thứ tự class dựa trên Alphabet tên thư mục lúc train.
        # Thường là: 0=Junk, 1=Normal (J đứng trước N trong bảng chữ cái?)
        # À khoan, J (Junk) đứng trước N (Normal).
        # => Class 0 = Junk, Class 1 = Normal.
        
        print("\n" + "="*30)
        print(f"🎯 KẾT QUẢ DỰ ĐOÁN:")
        print(f"Điểm số thô (Raw Score): {score:.4f}")
        
        if score < 0.5:
            confidence = (1 - score) * 100
            print(f"👉 AI chốt: 🗑️ ẢNH RÁC (Junk)")
            print(f"👉 Độ tin cậy: {confidence:.2f}%")
        else:
            confidence = score * 100
            print(f"👉 AI chốt: ✅ ẢNH THƯỜNG (Normal)")
            print(f"👉 Độ tin cậy: {confidence:.2f}%")
        print("="*30 + "\n")
        
    except Exception as e:
        print(f"❌ Lỗi khi đọc ảnh: {e}")

if __name__ == "__main__":
    predict_single_image()