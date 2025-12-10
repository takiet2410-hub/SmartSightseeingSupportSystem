import pandas as pd
from core.config import settings
from core.db import get_db_collection
from modules.vectorizer import HybridVectorizer
import sys
import os
from typing import List
import unicodedata
import time
from pymongo.errors import AutoReconnect

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 1. HÀM CHUẨN HÓA CƠ BẢN
def standardize_text(text):
    if not text:
        return ""
    text = str(text)
    text = unicodedata.normalize('NFC', text)
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    return text.strip().lower()

# 2. HÀM TÁCH CHUỖI DÙNG DẤU CHẤM PHẨY (,)
def process_tags_to_array(text_input):
    if not text_input:
        return []
    
    text_str = str(text_input)
    # Tách bằng dấu chấm phẩy
    raw_tags = text_str.split(',')
    
    cleaned_tags = []
    for tag in raw_tags:
        std_tag = standardize_text(tag)
        if std_tag:
            cleaned_tags.append(std_tag)
            
    return cleaned_tags

def get_corpus(df: pd.DataFrame) -> List[str]:
    corpus = []
    for _, row in df.iterrows():
        text_chunk = (
            f"Name: {row.get('name', '')}. "
            f"Location: {row.get('location_province', '')}, {row.get('specific_address', '')}. "
            f"Rating: {row.get('overall_rating', '')}/5. "
            f"Description: {row.get('info_summary', '')}. "
            f"Tags: {row.get('combined_tags', '')}. "
            f"Season: {row.get('season_tags', '')}."
            f"Budget range: {row.get('budget_range', '')}."
            f"Available time: {row.get('available_time_needed', '')}."
            f"Companion: {row.get('companion_tags', '')}."
        )
        corpus.append(text_chunk)
    return corpus

# --- 3. HÀM BATCH INSERT AN TOÀN (FIX LỖI 10054) ---
def batch_insert(collection, documents, batch_size=20):
    """
    Chia nhỏ dữ liệu để insert từng phần.
    batch_size=20: Mỗi lần chỉ gửi 20 địa điểm để tránh sập kết nối.
    """
    total_docs = len(documents)
    print(f"🚀 Starting SAFE batch insertion for {total_docs} documents...")
    
    for i in range(0, total_docs, batch_size):
        batch = documents[i : i + batch_size]
        max_retries = 3
        
        for attempt in range(max_retries):
            try:
                collection.insert_many(batch)
                print(f"   ✅ Inserted batch {i // batch_size + 1} ({len(batch)} items)")
                break # Thành công thì thoát vòng lặp retry
            except AutoReconnect:
                print(f"   ⚠️ Connection lost. Retrying batch {i // batch_size + 1} (Attempt {attempt+1}/{max_retries})...")
                time.sleep(2) # Đợi 2 giây trước khi thử lại
            except Exception as e:
                print(f"   ❌ Error inserting batch {i // batch_size + 1}: {e}")
                break # Lỗi khác (dữ liệu sai) thì bỏ qua batch này

def run_ingestion():
    print("--- STARTING DATA INGESTION ---")
    collection = get_db_collection()
    
    if collection is None:
        print("❌ Database connection failed.")
        return

    file_path = settings.EXCEL_FILE_PATH
    print(f"📂 Reading data from: {file_path}")

    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, engine='openpyxl')
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        return

    # Xử lý rating
    df['overall_rating'] = pd.to_numeric(df['overall_rating'], errors='coerce').fillna(0.0)
    df = df.fillna('')

    corpus = get_corpus(df)
    vectorizer = HybridVectorizer()
    
    print("🧠 Fitting vectorizer (This may take a moment)...")
    vectorizer.fit(corpus)
    
    # Kiểm tra số chiều vector để debug
    sample_vec = vectorizer.transform_single("test")
    print(f"ℹ️  VECTOR DIMENSION: {len(sample_vec)} (Make sure MongoDB Atlas Index matches this!)")
    
    documents_to_insert = []
    
    print(f"🔄 Processing {len(df)} rows...")
    for index, row in df.iterrows():
        text_chunk = corpus[index]
        hybrid_vector = vectorizer.transform_single(text_chunk)
        
        # Xử lý tags thành mảng (dùng hàm mới split theo ;)
        combined_tags = process_tags_to_array(row.get('combined_tags', ''))
        available_time_tags = process_tags_to_array(row.get('available_time_needed', ''))
        season_tags = process_tags_to_array(row.get('season_tags', ''))
        companion_tags = process_tags_to_array(row.get('companion_tags', ''))
        
        doc = {
            "landmark_id": str(row.get('landmark_id')),
            "name": row.get('name'),
            "text_chunk": text_chunk,
            "v_hybrid": hybrid_vector,
            
            "location_province": str(row.get('location_province', '')).strip(),
            "specific_address": str(row.get('specific_address', '')).strip(),
            "overall_rating": float(row.get('overall_rating', 0.0)),
            
            "budget_range": standardize_text(row.get('budget_range', '')),
            
            # Key chuẩn số ít để khớp với API retrieval
            "available_time": available_time_tags,
            "companion_tag": companion_tags,
            "season_tag": season_tags,
            "combined_tags": combined_tags,
            
            "description": row.get('info_summary'),
            "image_urls": str(row.get('image_urls', '')).split(';')
        }
        
        documents_to_insert.append(doc)

    if documents_to_insert:
        print(f"🗑️  Clearing old data...")
        try:
            collection.delete_many({})
        except Exception as e:
            print(f"Warning clearing data: {e}")

        # --- THAY ĐỔI QUAN TRỌNG NHẤT Ở ĐÂY ---
        # Không dùng insert_many trực tiếp nữa
        # Dùng batch_insert với kích thước nhỏ (20)
        batch_insert(collection, documents_to_insert, batch_size=20)
        
        print("✅ Ingestion complete. Data is safe.")

if __name__ == "__main__":
    run_ingestion()