import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer 
from sentence_transformers import SentenceTransformer 
from typing import List
import joblib
from core.config import settings

class HybridVectorizer:
    def __init__(self, model_name='keepitreal/vietnamese-sbert'):
        self.tfidf_vectorizer = TfidfVectorizer()
        self.sentence_transformer = SentenceTransformer(model_name) 

    def fit(self, corpus: List[str]):
        """
        Fit (huấn luyện) TfidfVectorizer trên toàn bộ corpus.
        """
        print("Fitting TF-IDF Vectorizer...")
        self.tfidf_vectorizer.fit(corpus)
        print("TF-IDF fitting complete.")
        
        # Lưu lại vectorizer đã fit
        joblib.dump(self.tfidf_vectorizer, settings.VECTORIZER_PATH)
        print(f"TF-IDF Vectorizer saved to {settings.VECTORIZER_PATH}")

    def load_fitted_tfidf(self, path: str):
        """
        Tải TF-IDF vectorizer đã được fit từ file.
        """
        try:
            self.tfidf_vectorizer = joblib.load(path)
            print(f"Loaded fitted TF-IDF from {path}")
        except FileNotFoundError:
            print(f"Error: Fitted TF-IDF file not found at {path}. Run ingest_data.py first.")
            # Xử lý lỗi
            
    def transform_single(self, text: str) -> np.ndarray:
        """
        Tạo hybrid vector cho một chunk text hoặc một query.
        """
        # 1. TF-IDF vector (Sparse matrix -> dense array)
        tfidf_vec = self.tfidf_vectorizer.transform([text]).toarray()
        
        # 2. Semantic (ST) vector
        semantic_vec = self.sentence_transformer.encode([text])
        
        # 3. Kết hợp (concatenate)
        hybrid_vec = np.concatenate([tfidf_vec, semantic_vec], axis=1)
        
        # Chuyển về list float cơ bản để dùng với MongoDB/JSON
        return hybrid_vec[0].tolist()