import pandas as pd
from core.config import settings
from core.db import get_db_collection
from modules.vectorizer import HybridVectorizer
import sys
import os
from typing import List
import unicodedata  

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def clean_split_tags(tag_string):
    if not isinstance(tag_string, str):
        return []
    return [t.strip() for t in tag_string.split(',') if t.strip()]

# 2. HÀM CHUẨN HÓA DỮ LIỆU 
def standardize_text(text):
    """
    - Chuyển về str.
    - Chuẩn hóa Unicode NFC (tránh lỗi font).
    - Thay thế gạch ngang Excel (–) bằng gạch thường (-).
    - Chuyển về chữ thường (lowercase).
    - Xóa khoảng trắng thừa.
    """
    if not text:
        return ""
    text = str(text)
    # Chuẩn hóa Unicode (NFC)
    text = unicodedata.normalize('NFC', text)
    # Thay thế các loại dấu gạch ngang lạ
    text = text.replace('\u2013', '-').replace('\u2014', '-')
    return text.strip().lower()

def get_corpus(df: pd.DataFrame) -> List[str]:
    corpus = []
    for _, row in df.iterrows():
        text_chunk = (
            f"Name: {row.get('name', '')}. "
            f"Location: {row.get('location_province', '')}, {row.get('specific_address', '')}. "
            f"Rating: {row.get('overall_rating', '')}/5. " 
            f"Description: {row.get('info_summary', '')}. "
            f"Tags: {row.get('activity_tags & vibe_tags (Combined_tags)', '')}. "
            f"Season: {row.get('season_tags', '')}."
            f"Budget range: {row.get('budget_range', '')}."
            f"Available time: {row.get('available_time_needed', '')}."
            f"Companion: {row.get('companion_tags', '')}."
        )
        corpus.append(text_chunk)
    return corpus

def run_ingestion():
    print("Starting data ingestion...")
    collection = get_db_collection()
    
    if collection is None:
        print("Database connection failed.")
        return

    file_path = settings.EXCEL_FILE_PATH 
    print(f"Reading data from: {file_path}")

    try:
        if file_path.endswith('.csv'):
            df = pd.read_csv(file_path)
        else:
            df = pd.read_excel(file_path, engine='openpyxl')
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Xử lý rating
    df['overall_rating'] = pd.to_numeric(df['overall_rating'], errors='coerce').fillna(0.0)
    df = df.fillna('') 

    corpus = get_corpus(df)
    vectorizer = HybridVectorizer()
    vectorizer.fit(corpus) 
    
    documents_to_insert = []
    
    print(f"Processing {len(df)} rows...")
    for index, row in df.iterrows():
        text_chunk = corpus[index] 
        hybrid_vector = vectorizer.transform_single(text_chunk) 
        
        combined_tags = clean_split_tags(row.get('activity_tags & vibe_tags (Combined_tags)', ''))
        
        doc = {
            "landmark_id": str(row.get('landmark_id')), 
            "name": row.get('name'),
            "text_chunk": text_chunk, 
            "v_hybrid": hybrid_vector, 
            
            "location_province": str(row.get('location_province', '')).strip(),
            "specific_address": str(row.get('specific_address', '')).strip(),
            "overall_rating": float(row.get('overall_rating', 0.0)),
            
            # === 3. ÁP DỤNG CHUẨN HÓA CHO CÁC TRƯỜNG FILTER ===
            # Dữ liệu vào DB sẽ sạch sẽ: "1-2 giờ", "thấp", "mùa hè" (lowercase, chuẩn dấu)
            "budget_range": standardize_text(row.get('budget_range', '')), 
            "available_time": standardize_text(row.get('available_time_needed', '')),
            "companion_tag": standardize_text(row.get('companion_tags', '')),
            "season_tag": standardize_text(row.get('season_tags', '')),
            # ==================================================

            "combined_tags_array": combined_tags,
            "description": row.get('info_summary'),
            "image_urls": str(row.get('image_urls', '')).split(';')
        }
        
        documents_to_insert.append(doc)

    if documents_to_insert:
        print(f"Inserting {len(documents_to_insert)} documents into MongoDB...")
        collection.delete_many({}) 
        collection.insert_many(documents_to_insert) 
        print("Ingestion complete. Data is now CLEAN and NORMALIZED.") 

if __name__ == "__main__":
    run_ingestion()