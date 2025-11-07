import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
from sentence_transformers import SentenceTransformer
from joblib import dump, load

# ===============================
# 1️⃣ Load dữ liệu
# ===============================
def load_data(path="vietnam_provinces.csv"):
    df = pd.read_csv(path)
    df["description"] = df["description_vi"] + " " + df["description_en"]
    return df


# ===============================
# 2️⃣ Xây dựng mô hình Hybrid
# ===============================
def build_hybrid_model(df, alpha=0.6, beta=0.4):
    print("🔹 Đang khởi tạo mô hình TF-IDF...")
    vectorizer = TfidfVectorizer(stop_words="english", max_df=0.8, ngram_range=(1, 2))
    tfidf_matrix = vectorizer.fit_transform(df["description"]).toarray()

    print("🔹 Đang tải SentenceTransformer (multilingual)...")
    model = SentenceTransformer("intfloat/multilingual-e5-base")
    embed_matrix = model.encode(df["description"], normalize_embeddings=True)

    # Chuẩn hóa TF-IDF
    tfidf_norm = tfidf_matrix / np.linalg.norm(tfidf_matrix, axis=1, keepdims=True)

    # Ghép vector
    hybrid_features = np.hstack([
        alpha * tfidf_norm,
        beta * embed_matrix
    ])

    # Huấn luyện KNN
    print("🔹 Đang huấn luyện KNN...")
    knn = NearestNeighbors(n_neighbors=5, metric="cosine")
    knn.fit(hybrid_features)

    print("✅ Huấn luyện xong Hybrid-KNN.")
    return vectorizer, model, knn, hybrid_features


# ===============================
# 3️⃣ Gợi ý điểm đến
# ===============================
def recommend_destinations(query, df, vectorizer, model, knn, alpha=0.6, beta=0.4, top_k=5):
    # Encode query
    q_tfidf = vectorizer.transform([query]).toarray()
    q_embed = model.encode([query], normalize_embeddings=True)

    # Chuẩn hóa & kết hợp
    q_hybrid = np.hstack([
        alpha * q_tfidf / np.linalg.norm(q_tfidf, axis=1, keepdims=True),
        beta * q_embed
    ])

    # Truy vấn KNN
    distances, indices = knn.kneighbors(q_hybrid)

    print(f"\n🔍 Kết quả gợi ý cho: '{query}'\n")
    for i, idx in enumerate(indices[0]):
        score = 1 - distances[0][i]
        print(f"{i+1}. {df.iloc[idx]['province']} (score={score:.3f}) – {df.iloc[idx]['description_vi']}")


# ===============================
# 4️⃣ Lưu / tải mô hình (tuỳ chọn)
# ===============================
def save_model(vectorizer, model, knn):
    dump(vectorizer, "tfidf_vectorizer.pkl")
    dump(knn, "knn_hybrid.pkl")
    model.save("sentence_transformer/")
    print("💾 Đã lưu mô hình TF-IDF, KNN, SentenceTransformer.")


def load_model():
    vectorizer = load("tfidf_vectorizer.pkl")
    knn = load("knn_hybrid.pkl")
    model = SentenceTransformer("sentence_transformer/")
    print("📦 Đã tải lại mô hình.")
    return vectorizer, model, knn


# ===============================
# 5️⃣ Chạy thử (Demo)
# ===============================
if __name__ == "__main__":
    # 1. Load dữ liệu
    df = load_data("vietnam_provinces.csv")

    # 2. Build model
    vectorizer, model, knn, hybrid_features = build_hybrid_model(df)

    # 3. Input
    test_queries = [
        "Tôi muốn ngắm sao trên trời",
        "Tôi thích khám phá thiên nhiên và khí hậu mát mẻ",
        "Tôi muốn trải nghiệm văn hóa truyền thống và di sản",
        "Tôi muốn nơi sôi động, có nhiều món ăn ngon và cuộc sống về đêm"
    ]

    for query in test_queries:
        recommend_destinations(query, df, vectorizer, model, knn)
