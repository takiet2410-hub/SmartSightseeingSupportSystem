import cv2
import numpy as np
import mediapipe as mp
import os

class CurationService:
    def __init__(self):
        # Khởi tạo MediaPipe Face Detection (Model nhẹ, chạy CPU tốt)
        self.mp_face_detection = mp.solutions.face_detection
        self.face_detection = self.mp_face_detection.FaceDetection(min_detection_confidence=0.5)

    def _get_blur_score(self, image):
        """
        Tính độ nét (Laplacian Variance).
        Càng cao càng nét. Thường > 100 là chấp nhận được.
        """
        try:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            score = cv2.Laplacian(gray, cv2.CV_64F).var()
            return score
        except:
            return 0.0

    def _get_brightness_score(self, image):
        """
        Tính điểm ánh sáng. 
        Thang điểm 0.0 -> 1.0 (1.0 là độ sáng lý tưởng ~128).
        """
        try:
            hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
            brightness = hsv[..., 2].mean()
            # Điểm cao nhất nếu brightness gần 128, thấp dần nếu quá tối (0) hoặc cháy sáng (255)
            score = 1.0 - (abs(brightness - 128) / 128)
            return max(0.0, score)
        except:
            return 0.0

    def _get_face_score(self, image):
        """
        Tính điểm khuôn mặt.
        Ưu tiên ảnh có mặt người, mặt càng to (rõ) điểm càng cao.
        """
        try:
            img_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            results = self.face_detection.process(img_rgb)

            if not results.detections:
                return 0.0

            max_face_area = 0.0
            face_count = 0

            for detection in results.detections:
                face_count += 1
                bbox = detection.location_data.relative_bounding_box
                area = bbox.width * bbox.height
                if area > max_face_area:
                    max_face_area = area
            
            # Công thức: (Có mặt + Diện tích mặt lớn nhất)
            # max_face_area thường nhỏ (vd 0.1 màn hình), nhân lên để có trọng số tốt
            score = min((face_count * 0.1) + (max_face_area * 5.0), 1.0)
            return score
        except:
            return 0.0

    def calculate_score(self, image_path):
        """
        Chấm điểm tổng hợp cho 1 ảnh.
        """
        if not os.path.exists(image_path):
            return 0.0

        try:
            image = cv2.imread(image_path)
            if image is None:
                return 0.0

            # 1. Tính các điểm thành phần
            raw_blur = self._get_blur_score(image)
            norm_blur = min(raw_blur / 500.0, 1.0) # Chuẩn hóa blur (giả sử 500 là rất nét)
            
            score_bright = self._get_brightness_score(image)
            score_face = self._get_face_score(image)

            # 2. Trọng số (Weights) - Có thể điều chỉnh
            W_BLUR = 0.3
            W_BRIGHT = 0.2
            W_FACE = 0.5  # Ưu tiên cao nhất cho ảnh có người

            total_score = (norm_blur * W_BLUR) + (score_bright * W_BRIGHT) + (score_face * W_FACE)
            
            return round(total_score, 4)
        except Exception as e:
            print(f"Lỗi chấm điểm {image_path}: {e}")
            return 0.0

    def select_best_shot(self, image_paths: list):
        """
        Chọn ảnh tốt nhất từ danh sách.
        Trả về: (best_image_path, best_score, all_scores)
        """
        if not image_paths:
            return None, 0.0, []

        scores = []
        for path in image_paths:
            s = self.calculate_score(path)
            scores.append({"path": path, "score": s})

        # Sắp xếp giảm dần theo điểm
        scores.sort(key=lambda x: x["score"], reverse=True)
        
        best_shot = scores[0]
        return best_shot["path"], best_shot["score"], scores