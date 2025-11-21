import cv2
import numpy as np
import os

class LightingFilter:
    def __init__(self):
        # --- CẤU HÌNH NGƯỠNG (THRESHOLDS) ---
        # 1. Ngưỡng tối: Dưới mức này là "Tối thui"
        self.MIN_BRIGHTNESS = 40.0 
        
        # 2. Ngưỡng sáng: Trên mức này là "Chói lòa" (toàn bộ ảnh)
        self.MAX_BRIGHTNESS = 220.0 
        
        # 3. Ngưỡng lóa (Glare): Nếu số lượng pixel trắng tinh (>=250)
        # chiếm quá bao nhiêu % bức ảnh? (0.3 = 30% diện tích ảnh)
        self.GLARE_RATIO_THRESHOLD = 0.30 

    def analyze_image(self, image_path):
        """
        Phân tích ánh sáng của một bức ảnh.
        Trả về: (Trạng thái, Lý do, Giá trị đo được)
        """
        try:
            # Đọc ảnh
            img = cv2.imread(image_path)
            if img is None:
                return False, "Error reading file", 0

            # Chuyển sang hệ màu HSV để lấy kênh V (Value - Độ sáng)
            # Đây là cách chuẩn hơn so với việc convert sang Gray
            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            v_channel = hsv[:, :, 2] # Kênh thứ 3 là V

            # 1. Tính độ sáng trung bình
            mean_brightness = np.mean(v_channel)

            # 2. Tính tỷ lệ điểm "cháy" (Glare)
            # Đếm số pixel có độ sáng > 250
            num_glare_pixels = np.sum(v_channel > 250)
            total_pixels = v_channel.size
            glare_ratio = num_glare_pixels / total_pixels

            # --- QUYẾT ĐỊNH ---
            
            # Kiểm tra Tối
            if mean_brightness < self.MIN_BRIGHTNESS:
                return False, "Quá tối (Underexposed)", mean_brightness

            # Kiểm tra Chói toàn phần
            if mean_brightness > self.MAX_BRIGHTNESS:
                return False, "Quá sáng (Overexposed)", mean_brightness

            # Kiểm tra Lóa cục bộ (Glare/Burned)
            if glare_ratio > self.GLARE_RATIO_THRESHOLD:
                return False, f"Bị lóa/Cháy sáng ({glare_ratio*100:.1f}%)", glare_ratio

            # Nếu qua hết các bài test -> Ảnh tốt
            return True, "Ánh sáng tốt", mean_brightness

        except Exception as e:
            print(f"Lỗi xử lý {image_path}: {e}")
            return True, "Error skipped", 0

# --- SCRIPT CHẠY THỬ ---
if __name__ == "__main__":
    # Thay đổi đường dẫn tới folder chứa ảnh test của bạn
    TEST_DIR = r"E:\WorkPlace\First\Normal_Source" 
    
    # Lấy 10 ảnh để test
    import glob
    test_images = glob.glob(os.path.join(TEST_DIR, "*.*"))[:10]

    processor = LightingFilter()

    print(f"{'FILENAME':<30} | {'KẾT QUẢ':<15} | {'LÝ DO'}")
    print("-" * 80)

    for img_path in test_images:
        is_good, reason, score = processor.analyze_image(img_path)
        
        filename = os.path.basename(img_path)
        status = "✅ PASS" if is_good else "❌ REJECT"
        
        print(f"{filename[:28]:<30} | {status:<15} | {reason} (Score: {score:.2f})")