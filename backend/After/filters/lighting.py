import cv2
from typing import Tuple, Union
import numpy as np
from PIL import Image

class LightingFilter:
    def __init__(self):
        self.MIN_BRIGHTNESS = 40.0 
        self.MAX_BRIGHTNESS = 220.0 
        self.GLARE_RATIO_THRESHOLD = 0.30 

    def analyze(self, image_path: str) -> Tuple[bool, str]:
        """
        Original method: Load from disk
        Returns: (is_good: bool, reason: str)
        """
        try:
            img = cv2.imread(image_path)
            if img is None:
                return False, "Corrupt Image"
            return self._analyze_internal(img)
        except Exception as e:
            return True, f"Lighting Check Failed: {e}"
    
    def analyze_from_image(self, pil_image: Image.Image) -> Tuple[bool, str]:
        """
        🚀 V2.1: Accept PIL Image directly (avoid disk read)
        Used for thumbnail processing - faster!
        """
        try:
            # Convert PIL -> OpenCV BGR
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            img_array = np.array(pil_image)
            img_bgr = cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
            
            return self._analyze_internal(img_bgr)
        except Exception as e:
            return True, f"Lighting Check Failed: {e}"
    
    def _analyze_internal(self, img_bgr: np.ndarray) -> Tuple[bool, str]:
        """Shared analysis logic"""
        try:
            hsv = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2HSV)
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
            return True, f"Lighting Check Failed: {e}"