import os
import threading

import numpy as np
import tf_keras as keras
from tf_keras.models import load_model
from tf_keras.preprocessing import image

from logger_config import logger

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'

# Singleton Cache
_junk_model = None
_model_lock = threading.Lock()

def get_model():
    global _junk_model
    
    if _junk_model is not None: return _junk_model
    
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

def is_junk(image_path: str) -> bool:
    """Single image junk detection (kept for backwards compatibility)"""
    return is_junk_batch([image_path])[0]

def is_junk_batch(image_paths: list) -> list:
    """
    🚀 OPTIMIZED: Batch junk detection for multiple images
    Returns list of boolean values
    """
    model = get_model()
    if not model: 
        return [False] * len(image_paths)

    try:
        # Batch load and preprocess
        batch_images = []
        valid_indices = []
        
        for idx, path in enumerate(image_paths):
            try:
                img = image.load_img(path, target_size=(224, 224))
                x = image.img_to_array(img)
                batch_images.append(x)
                valid_indices.append(idx)
            except Exception as e:
                logger.error(f"Failed to load {path}: {e}")
                continue
        
        if not batch_images:
            return [False] * len(image_paths)
        
        # Stack into batch
        batch_array = np.array(batch_images) / 255.0
        
        # Batch predict (much faster!)
        predictions = model.predict(batch_array, verbose=0, batch_size=32)
        
        # Map results back
        results = [False] * len(image_paths)
        for idx, pred in zip(valid_indices, predictions):
            results[idx] = pred[0] < 0.5
        
        return results

    except Exception as e:
        logger.error(f"Batch Junk Inference Failed: {e}")
        return [False] * len(image_paths)