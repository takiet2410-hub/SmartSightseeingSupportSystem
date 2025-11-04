# 🧭 Vibe Recommendation Pipeline – Smart Tourism System (Context 2)

## 1️⃣ Mục tiêu

Pipeline này xử lý **ý định trừu tượng (vibe)** của người dùng – ví dụ:

> “tôi muốn đi nơi yên bình, nhiều cây xanh, khí hậu mát mẻ”

Mục tiêu là **tìm các địa điểm du lịch có cảm xúc tương đồng nhất** trong cơ sở dữ liệu (CSDL) thông qua mô hình **SentenceTransformer + TF-IDF + Cosine Similarity + KNN**.

---

## 2️⃣ Tổng quan pipeline

Người dùng nhập vibe
↓
Vector hóa (TF-IDF + SentenceTransformer)
↓
Tính độ tương đồng (Cosine Similarity)
↓
Tìm top địa điểm gần nhất (KNN / Ranking)
↓
Trả về gợi ý địa điểm phù hợp


---

## 3️⃣ Các thành phần chi tiết

### 🔹 3.1 TF-IDF (Term Frequency - Inverse Document Frequency)

TF-IDF đánh giá tầm quan trọng của một từ trong tập văn bản.

\[
\text{TF-IDF}(t,d) = TF(t,d) \times \log\left(\frac{N}{DF(t)}\right)
\]

- \(TF(t,d)\): tần suất của từ \(t\) trong tài liệu \(d\)  
- \(DF(t)\): số tài liệu chứa từ \(t\)  
- \(N\): tổng số tài liệu  

TF-IDF giúp mô hình nắm được **từ khóa đặc trưng** của từng địa điểm.

---

### 🔹 3.2 SentenceTransformer (Semantic Embedding)

#### 🧠 Tổng quan

**SentenceTransformer** là một mô hình học sâu dựa trên **BERT (Bidirectional Encoder Representations from Transformers)**, được tinh chỉnh để tạo ra vector biểu diễn (embedding) cho toàn bộ câu hoặc đoạn văn — thay vì từng từ riêng lẻ.

Mục tiêu của mô hình là ánh xạ các câu có **nghĩa tương tự** vào **những điểm gần nhau trong không gian vector**.

#### 🔬 Cấu trúc tổng quát
Chuỗi đầu vào (sentence)
↓
Tokenizer (chuyển từ → token ID)
↓
Transformer Encoder (BERT / MiniLM / DistilBERT)
↓
Pooling Layer (Mean / Max / CLS token)
↓
Sentence Embedding (vector ngữ nghĩa)

Mỗi câu sau khi đi qua mô hình sẽ được biểu diễn bằng một vector có 384–768 chiều (tuỳ model), ví dụ `all-MiniLM-L6-v2` tạo vector 384 chiều.

#### ⚙️ Cơ chế hoạt động chi tiết

1. **Tokenizer**  
Chuyển câu đầu vào thành chuỗi token ID, ví dụ: 
"Đà Lạt yên bình" → [101, 3912, 1652, 102]
(mã hóa dựa trên WordPiece Tokenization)

2. **Transformer Encoder**  
Áp dụng *multi-head self-attention*, cho phép mô hình nắm bắt quan hệ giữa các từ theo ngữ cảnh hai chiều:
\[
\text{Attention}(Q, K, V) = \text{softmax}\left(\frac{QK^T}{\sqrt{d_k}}\right) V
\]
Trong đó:
- \(Q, K, V\): ma trận truy vấn, khóa, giá trị  
- \(d_k\): kích thước không gian ẩn (hidden size)

3. **Pooling Layer**  
Trung bình hóa (mean pooling) toàn bộ token embedding thành một vector duy nhất:
\[
s = \frac{1}{n}\sum_{i=1}^{n}h_i
\]
với \(h_i\) là embedding của token thứ *i*.

4. **Sentence Embedding**  
Kết quả là vector ngữ nghĩa biểu diễn toàn câu, ví dụ:
[0.123, -0.041, 0.332, ... , 0.027]

#### 🧩 Trong bài toán Vibe Recommendation

Trong hệ thống du lịch thông minh, SentenceTransformer giúp:
- Hiểu **ngữ nghĩa sâu** của mô tả địa điểm (“thành phố mờ sương” ≈ “thời tiết mát lạnh, sương phủ”).
- Hiểu **vibe trừu tượng** từ người dùng (“chữa lành”, “yên bình”, “chill”).
- Kết nối các cách diễn đạt khác nhau có cùng nội dung cảm xúc.

Ví dụ:

| Vibe người dùng | Vibe địa điểm | Cosine Similarity |
|------------------|---------------|------------------|
| “yên tĩnh, khí hậu mát mẻ” | “không khí trong lành, nhiều cây thông” | 0.89 |
| “náo nhiệt, sôi động” | “biển, tiệc, lễ hội” | 0.86 |
| “chữa lành” | “spa, thiên nhiên, tĩnh tâm” | 0.81 |

Các vector embedding được chuẩn hóa và dùng để tính **cosine similarity**, giúp hệ thống gợi ý được các điểm du lịch phù hợp về *tâm trạng* chứ không chỉ dựa vào *từ khóa*.

#### 💡 Mô hình sử dụng

Trong pipeline hiện tại:
```python
from sentence_transformers import SentenceTransformer
st = SentenceTransformer("all-MiniLM-L6-v2")

---

## 4️⃣ Chuẩn hóa pipeline hybrid (TF-IDF + SentenceTransformer)

Ta kết hợp hai loại vector để tận dụng cả **ngữ nghĩa** và **từ khóa**:

\[
V_{hybrid} = [V_{TFIDF} ; V_{ST}]
\]

(tức là nối 2 vector theo chiều ngang)

---

## 5️⃣ Cosine Similarity

Độ đo tương đồng giữa hai vector:

\[
\text{cosine\_similarity}(A, B) = \frac{A \cdot B}{\|A\| \times \|B\|}
\]

Giá trị:
- 1 → giống hệt  
- 0 → không liên quan  
- -1 → trái ngược  

---

## 6️⃣ KNN (K-Nearest Neighbors)

KNN tìm **k điểm gần nhất** với vector đầu vào trong không gian cosine.

\[
d_{cos}(A,B) = 1 - \text{cosine\_similarity}(A,B)
\]

→ Chọn **k địa điểm có khoảng cách nhỏ nhất** để gợi ý.

---

## 7️⃣ Code triển khai chuẩn hóa pipeline

### 🔸 Import thư viện
```python
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.neighbors import NearestNeighbors
from sentence_transformers import SentenceTransformer

df = pd.DataFrame({
    "name": ["Đà Lạt", "Nha Trang", "Hội An", "Sa Pa"],
    "description": [
        "yên tĩnh, nhiều cây thông, khí hậu mát mẻ, chữa lành",
        "biển, năng động, náo nhiệt, lặn biển, vui chơi",
        "cổ kính, yên bình, di sản, văn hóa, truyền thống",
        "núi, lạnh, thiên nhiên, hùng vĩ, yên bình"
    ]
})

1. TF-IDF Vectorization
tfidf = TfidfVectorizer(max_features=5000)
tfidf_vecs = tfidf.fit_transform(df["description"])
tfidf_vecs = normalize(tfidf_vecs)

2. SentenceTransformer Embedding
st = SentenceTransformer("all-MiniLM-L6-v2")
st_vecs = st.encode(df["description"].tolist(), convert_to_numpy=True)
st_vecs = normalize(st_vecs)

3. Tạo Hybrid Vector
hybrid_vecs = np.concatenate([tfidf_vecs.toarray(), st_vecs], axis=1)

4. Tạo KNN Model
knn = NearestNeighbors(metric="cosine", n_neighbors=3)
knn.fit(hybrid_vecs)

5. Vector hóa input người dùng
user_vibe = "tôi muốn đi nơi yên bình, nhiều cây xanh, khí hậu mát mẻ"

user_tfidf = tfidf.transform([user_vibe]).toarray()
user_st = st.encode([user_vibe], convert_to_numpy=True)
user_vec = np.concatenate([user_tfidf, user_st], axis=1)
user_vec = normalize(user_vec)

6. Tính Cosine Similarity + KNN gợi ý
# Cosine Similarity
sim_scores = cosine_similarity(user_vec, hybrid_vecs).flatten()

# KNN
distances, indices = knn.kneighbors(user_vec)

# Hiển thị kết quả
for idx in indices[0]:
    print(f"🏞 {df['name'][idx]} — similarity: {sim_scores[idx]:.3f}"

💡 Kết quả mẫu
🏞 Đà Lạt — similarity: 0.893
🏞 Sa Pa — similarity: 0.752
🏞 Hội An — similarity: 0.640

## 8️⃣ Tổng hợp công thức pipeline

Độ tương đồng giữa "vibe" của người dùng và mỗi địa điểm được tính bằng **Cosine Similarity** giữa hai vector hybrid (TF-IDF + SentenceTransformer):

\[
\text{Sim}(u, i) = \cos\left( [TFIDF(u); ST(u)], [TFIDF(i); ST(i)] \right)
\]

Trong đó:
- **u**: vector vibe của người dùng  
- **i**: vector đặc trưng của địa điểm trong CSDL  
- **cos**: hàm cosine similarity  

Nếu sử dụng KNN để lấy *k* điểm gần nhất:

\[
\text{Top}_k = \text{argsort}_i(1 - \text{Sim}(u, i))[:k]
\]

---

## 9️⃣ Ưu điểm của mô hình hybrid

| Phương pháp | Ưu điểm | Hạn chế |
|--------------|----------|----------|
| **TF-IDF** | Hiểu rõ từ khóa cụ thể (ví dụ “biển”, “núi”) | Không hiểu ngữ nghĩa |
| **SentenceTransformer** | Hiểu ngữ cảnh, từ đồng nghĩa, diễn đạt tự nhiên | Tốn bộ nhớ hơn |
| **KNN** | Truy vấn nhanh top-k điểm tương tự | Không học tham số |
| **Cosine Similarity** | Đơn giản, hiệu quả trong không gian vector | Không mô hình hóa phi tuyến |

---

## 🔟 Ứng dụng trong hệ thống du lịch thông minh

| Mô-đun | Vai trò |
|--------|----------|
| **Context 1** | Thu thập dữ liệu (Overpass API + Wikipedia) |
| **Context 2** | Xử lý Vibe (TF-IDF + SentenceTransformer + KNN) |
| **Context 3** | Tổng hợp điểm (thời tiết, khoảng cách, rating, cảm xúc) |
| **Context 4** | Gợi ý cuối cùng cho người dùng |
