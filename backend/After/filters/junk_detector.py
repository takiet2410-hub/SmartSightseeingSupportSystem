import os
import threading

import numpy as np
import tf_keras as keras
from tf_keras.models import load_model
from tf_keras.preprocessing import image
from PIL import Image

from logger_config import logger

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Singleton Cache
_junk_model = None
_model_lock = threading.Lock()

def get_model():
    global _junk_model
    
    if _junk_model is not None: 
        return _junk_model
    
    with _model_lock:
        if _junk_model is not None:
            return _junk_model
        
        model_path = os.path.join("models", "junk_filter_model_v3.h5")
        if not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            return None
        
        logger.info("Loading Junk Filter Model (TensorFlow)...")
        _junk_model = load_model(model_path)
        logger.info("Junk Filter Model Loaded")
        
        return _junk_model

def has_camera_model(image_path: str) -> bool:
    """
    Check if image has Camera Model Name in EXIF data.
    Returns True if camera model exists, False otherwise.
    """
    try:
        img = Image.open(image_path)
        
        # Try to get EXIF data
        exif_data = None
        if hasattr(img, 'getexif') and callable(img.getexif):
            exif_dict = img.getexif()
            if exif_dict:
                exif_data = dict(exif_dict)
        elif hasattr(img, '_getexif') and callable(img._getexif):
            exif_data = img._getexif()
        
        if not exif_data:
            return False
        
        # Check for Camera Model (Tag 272 = Model, Tag 271 = Make)
        # A real photo should have at least one of these
        has_model = exif_data.get(272) is not None  # Model
        has_make = exif_data.get(271) is not None   # Make
        
        return has_model or has_make
        
    except Exception as e:
        logger.warning(f"Failed to check camera model for {image_path}: {e}")
        return False  # If we can't read EXIF, assume it's suspicious

def is_junk(image_path: str) -> bool:
    """Single image junk detection (kept for backwards compatibility)"""
    return is_junk_batch([image_path])[0]

def is_junk_batch(image_paths: list) -> list:
    """
    🚀 V3: Multi-stage junk detection
    Stage 1: Check for camera model (screenshots, downloads, memes won't have this)
    Stage 2: AI model prediction (existing logic)
    
    Returns list of boolean values (True = junk, False = good)
    """
    results = []
    ai_check_needed = []
    ai_check_indices = []
    
    # Stage 1: Camera Model Check
    for idx, path in enumerate(image_paths):
        if not has_camera_model(path):
            logger.info(f"🗑️ Marked as junk (no camera model): {path}")
            results.append(True)  # Junk - no camera metadata
        else:
            results.append(None)  # Need AI check
            ai_check_needed.append(path)
            ai_check_indices.append(idx)
    
    # Stage 2: AI Model Check (only for photos with camera metadata)
    if ai_check_needed:
        model = get_model()
        if not model:
            # If model fails, mark all as good (already passed camera check)
            for idx in ai_check_indices:
                results[idx] = False
            return results
        
        try:
            # Batch load and preprocess
            batch_images = []
            valid_indices = []
            
            for idx, path in enumerate(ai_check_needed):
                try:
                    img = image.load_img(path, target_size=(224, 224))
                    x = image.img_to_array(img)
                    batch_images.append(x)
                    valid_indices.append(idx)
                except Exception as e:
                    logger.error(f"Failed to load {path}: {e}")
                    continue
            
            if batch_images:
                # Stack into batch and normalize
                batch_array = np.array(batch_images) / 255.0
                
                # Batch predict
                predictions = model.predict(batch_array, verbose=0, batch_size=32)
                
                # Map AI results back
                for idx, pred in zip(valid_indices, predictions):
                    original_idx = ai_check_indices[idx]
                    results[original_idx] = pred[0] < 0.8  # <0.8 = junk
            
            # Mark any failed loads as good (benefit of doubt)
            for i, result in enumerate(results):
                if result is None:
                    results[i] = False
                    
        except Exception as e:
            logger.error(f"Batch Junk Inference Failed: {e}")
            # If AI fails, mark all as good (they passed camera check)
            for idx in ai_check_indices:
                if results[idx] is None:
                    results[idx] = False
    
    return results