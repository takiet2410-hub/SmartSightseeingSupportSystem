import os
import threading

import numpy as np
import tensorflow as tf
from tensorflow.keras.models import load_model
from tensorflow.keras.preprocessing import image

from logger_config import logger

os.environ['TF_CPP_MIN_LOG_LEVEL'] = '2'  # Suppress TensorFlow logging

# Singleton Cache
_junk_model = None
_model_lock = threading.Lock()

def get_model():
    global _junk_model
    
    if _junk_model is not None: return _junk_model
    
    with _model_lock:
        # Second check (prevent duplicate loading)
        if _junk_model is not None:
            return _junk_model
        
        model_path = os.path.join("models", "junk_filter_model_v3.h5")
        if not os.path.exists(model_path):
            logger.error(f"Model file not found: {model_path}")
            return None
        
        logger.info("Loading Junk Filter Model (TensorFlow)...")
        _junk_model = load_model(model_path)
        logger.info("Junk Filter Model Loaded ✓")
        
        return _junk_model

def is_junk(image_path: str) -> bool:
    """
    Returns True if image is Junk, False if good.
    Assumes model input size is 224x224 (Standard). 
    Change target_size if your teammate used something else!
    """
    model = get_model()
    if not model: return False # Fail safe

    try:
        # 1. Preprocess
        img = image.load_img(image_path, target_size=(224, 224))
        x = image.img_to_array(img)
        x = np.expand_dims(x, axis=0)
        x = x / 255.0 # Normalize if your model expects [0,1]

        # 2. Predict
        # Assuming binary output: 0=Good, 1=Junk (Or vice versa? Check with teammate!)
        # Let's assume prediction > 0.5 is Junk
        prediction = model.predict(x, verbose=0)[0][0]
        
        is_junk_detected = prediction < 0.5
        return is_junk_detected

    except Exception as e:
        logger.error(f"Junk Inference Failed: {e}")
        return False