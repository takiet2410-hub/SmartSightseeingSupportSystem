"""
Vibe Processor – Smart Tourism System (Context 2)
-------------------------------------------------
Module xử lý "Vibe" (Abstract Interest Processor):
 - Vector hóa tags du lịch bằng TF-IDF và SentenceTransformer
 - Nhận đầu vào "vibe" người dùng (VD: 'yên tĩnh, thiên nhiên, chữa lành')
 - Tính cosine similarity để tìm các địa điểm phù hợp

"""

import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import normalize
from sentence_transformers import SentenceTransformer


class VibeRecommender:
    def __init__(self, csv_path: str):
        """
        Khởi tạo hệ thống gợi ý Vibe.
        :param csv_path: đường dẫn tới dataset du lịch (đã enrich từ Overpass + Wikipedia)
        """
        self.df = pd.read_csv(csv_path, encoding="utf-8-sig")
        self.df["tags_vibe"] = (
            self.df["type"].fillna("") + " " + self.df["description"].fillna("")
        )

        print(f"✅ Dataset loaded: {len(self.df)} địa điểm")

        # --- TF-IDF ---
        self.tfidf = TfidfVectorizer(max_features=10000)
        self.tfidf_vectors = self.tfidf.fit_transform(self.df["tags_vibe"])
        self.tfidf_vectors = normalize(self.tfidf_vectors)

        # --- Sentence Transformer ---
        self.st_model = SentenceTransformer("all-MiniLM-L6-v2")
        self.st_embeddings = self.st_model.encode(
            self.df["tags_vibe"].tolist(), convert_to_numpy=True, show_progress_bar=True
        )
        self.st_embeddings = normalize(self.st_embeddings)

        # --- Hybrid Embedding ---
        self.hybrid_embeddings = np.concatenate(
            [self.tfidf_vectors.toarray(), self.st_embeddings], axis=1
        )

    def vectorize_input(self, vibe_text: str):
        """
        Biến vibe người dùng thành vector hybrid (TF-IDF + ST).
        """
        tfidf_vec = self.tfidf.transform([vibe_text]).toarray()
        st_vec = self.st_model.encode([vibe_text], convert_to_numpy=True)
        hybrid_vec = np.concatenate([tfidf_vec, st_vec], axis=1)
        return normalize(hybrid_vec)

    def recommend(self, vibe_text: str, top_k: int = 5):
        """
        Gợi ý địa điểm dựa trên vibe đầu vào người dùng.
        """
        vibe_vec = self.vectorize_input(vibe_text)
        sim_scores = cosine_similarity(vibe_vec, self.hybrid_embeddings).flatten()
        top_idx = sim_scores.argsort()[::-1][:top_k]

        results = []
        for i in top_idx:
            result = {
                "province": self.df.loc[i, "province"],
                "name": self.df.loc[i, "name"],
                "type": self.df.loc[i, "type"],
                "similarity": float(sim_scores[i]),
            }
            results.append(result)
        return pd.DataFrame(results)

"""
# === Demo chạy nhanh ===
if __name__ == "__main__":
    recommender = VibeRecommender("data/vietnam_tourism_enriched.csv")

    vibe_input = "tôi muốn đi nơi yên bình, khí hậu mát mẻ, nhiều cây xanh"
    recs = recommender.recommend(vibe_input, top_k=5)

    print("\n🎯 Gợi ý phù hợp nhất:")
    for _, row in recs.iterrows():
        print(f"🏞 {row['name']} ({row['province']}) — {row['type']} — score: {row['similarity']:.3f}")

"""