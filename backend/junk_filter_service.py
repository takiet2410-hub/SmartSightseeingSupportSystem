import tensorflow as tf
import numpy as np
from tensorflow.keras.preprocessing import image
from typing import List, Tuple
import os

from lighting_filter import LightingFilter
from schemas import PhotoObject, ProcessingDirective

class JunkFilterService:
    def __init__(self, model_path: str = 'junk_filter_model_v3.h5'):
        self.lighting_filter = LightingFilter()
        self.model = None
        self.img_size = (224, 224)
        
        # Load ML model if available
        if os.path.exists(model_path):
            try:
                self.model = tf.keras.models.load_model(model_path)
                print("ML Junk Filter model loaded")
            except Exception as e:
                print(f"Failed to load ML model: {e}")
        else:
            print(f"Model not found at {model_path}. Using lighting filter only.")
    
    def _check_lighting(self, image_path: str) -> Tuple[bool, str]:
        """Returns (is_good, reason)"""
        is_good, reason, _ = self.lighting_filter.analyze_image(image_path)
        return is_good, reason
    
    def _check_ml(self, image_path: str) -> Tuple[float, bool]:
        """Returns (junk_score, is_junk) where junk_score 0-1, higher = more junk"""
        if not self.model:
            return None, False
        
        try:
            img = image.load_img(image_path, target_size=self.img_size)
            img_array = image.img_to_array(img)
            img_array = img_array / 255.0
            img_array = np.expand_dims(img_array, axis=0)
            
            prediction = self.model.predict(img_array, verbose=0)
            score = prediction[0][0]  # Probability (0=Junk, 1=Normal)
            
            # Invert: higher junk_score = more likely junk
            junk_score = 1.0 - score
            is_junk = junk_score > 0.5
            
            return junk_score, is_junk
        
        except Exception as e:
            print(f"ML filter error on {image_path}: {e}")
            return None, False
    
    def filter_photo(self, photo: PhotoObject) -> PhotoObject:
        """
        Run all filters on a single photo.
        Updates photo object with filter results.
        Sets clustering_directive to JUNK_REJECTED if failed.
        """
        
        # 1. Lighting check
        lighting_ok, lighting_reason = self._check_lighting(photo.temp_file_path)
        photo.lighting_status = lighting_ok
        photo.lighting_reason = lighting_reason
        
        # 2. ML check
        junk_score, ml_is_junk = self._check_ml(photo.temp_file_path)
        photo.ml_junk_score = junk_score
        
        # 3. Final verdict
        # Reject if: lighting fails OR ML says junk
        if not lighting_ok or ml_is_junk:
            photo.is_junk = True
            photo.clustering_directive = ProcessingDirective.JUNK_REJECTED
        else:
            photo.is_junk = False
        
        return photo
    
    def filter_batch(self, photos: List[PhotoObject]) -> List[PhotoObject]:
        """Filter all photos in batch"""
        filtered = []
        rejected_count = 0
        
        for photo in photos:
            self.filter_photo(photo)
            filtered.append(photo)
            if photo.is_junk:
                rejected_count += 1
        
        if rejected_count > 0:
            print(f"--- Junk Filter: Rejected {rejected_count}/{len(photos)} photos ---")
        
        return filtered