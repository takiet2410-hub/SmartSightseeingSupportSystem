import cv2
import numpy as np
from typing import Tuple

class LightingFilter:
    def __init__(self):
        self.MIN_BRIGHTNESS = 40.0 
        self.MAX_BRIGHTNESS = 220.0 
        self.GLARE_RATIO_THRESHOLD = 0.30 

    def analyze(self, image_path: str) -> Tuple[bool, str]:
        """
        Returns: (is_good: bool, reason: str)
        """
        try:
            # OpenCV reads path directly
            img = cv2.imread(image_path)
            if img is None:
                return False, "Corrupt Image"

            hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
            v_channel = hsv[:, :, 2]

            mean_brightness = np.mean(v_channel)
            
            # Glare Calc
            num_glare_pixels = np.sum(v_channel > 250)
            total_pixels = v_channel.size
            glare_ratio = num_glare_pixels / total_pixels

            # Checks
            if mean_brightness < self.MIN_BRIGHTNESS:
                return False, "Underexposed (Too Dark)"

            if mean_brightness > self.MAX_BRIGHTNESS:
                return False, "Overexposed (Too Bright)"

            if glare_ratio > self.GLARE_RATIO_THRESHOLD:
                return False, f"Glare Detected ({glare_ratio*100:.0f}%)"

            return True, "Good Lighting"

        except Exception as e:
            return True, f"Lighting Check Failed: {e}" # Don't reject on code error