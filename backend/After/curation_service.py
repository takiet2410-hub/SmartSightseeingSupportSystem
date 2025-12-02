import cv2
import numpy as np
import mediapipe as mp
import os
from PIL import Image

class CurationService:
    def __init__(self):
        try:
            print("init MediaPipe...")
            self.mp_face_detection = mp.solutions.face_detection
            self.face_detection = self.mp_face_detection.FaceDetection(min_detection_confidence=0.5)
            print("MediaPipe Init Success")
        except Exception as e:
            print(f"CRITICAL: MediaPipe failed to load: {e}")
            self.face_detection = None

    def calculate_score(self, image_input) -> float:
        try:
            image_bgr = None

            # 1. Convert PIL -> OpenCV (BGR)
            if isinstance(image_input, Image.Image):
                if image_input.mode != 'RGB':
                    image_input = image_input.convert('RGB')
                image_bgr = cv2.cvtColor(np.array(image_input), cv2.COLOR_RGB2BGR)
            
            elif isinstance(image_input, str):
                image_bgr = cv2.imread(image_input)

            if image_bgr is None:
                print("Curation: Image is None")
                return 0.0

            # 2. RUN SCORING
            return self._calculate_internal(image_bgr)

        except Exception as e:
            print(f"Curation Crash: {e}")
            return 0.0

    def _calculate_internal(self, image_bgr) -> float:
        try:
            # --- BLUR ---
            gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
            raw_blur = cv2.Laplacian(gray, cv2.CV_64F).var()
            norm_blur = min(raw_blur / 500.0, 1.0)

            # --- BRIGHTNESS ---
            hsv = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2HSV)
            brightness = hsv[..., 2].mean()
            score_bright = 1.0 - (abs(brightness - 128) / 128)
            score_bright = max(0.0, score_bright)

            # --- FACE ---
            score_face = 0.0
            if self.face_detection:
                try:
                    img_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
                    results = self.face_detection.process(img_rgb)
                    if results.detections:
                        score_face = 1.0 # Found a face!
                except Exception as e:
                    print(f"MediaPipe Error: {e}")

            # --- TOTAL ---
            total = (norm_blur * 0.4) + (score_bright * 0.2) + (score_face * 0.4)
            
            return round(total, 4)

        except Exception as e:
            print(f"Internal Calc Failed: {e}")
            return 0.0