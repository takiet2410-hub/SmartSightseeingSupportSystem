import pandas as pd
from pymongo import MongoClient
from langchain_text_splitters import RecursiveCharacterTextSplitter
from core.config import settings
from core.db import get_db_collection
from modules.vectorizer import HybridVectorizer
import sys
import os
from typing import List

# Thêm đường dẫn gốc của dự án vào sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_corpus(df: pd.DataFrame) -> List[str]:
    """
    Kết hợp các trường văn bản 'tag' và 'description' thành một corpus.
    """
    corpus = []
    for _, row in df.iterrows():
        #
        text_chunk = f"Tags: {row.get('tag', '')}. Description: {row.get('description', '')}"
        corpus.append(text_chunk)
    return corpus

def run_ingestion():
    print("Starting data ingestion...")
    collection = get_db_collection()
    
    if collection is None:
        print("Database connection failed. Exiting ingestion.")
        return

    # 1. Đọc CSV
    try:
        df = pd.read_csv(settings.CSV_FILE_PATH) 
    except FileNotFoundError:
        print(f"Error: CSV file not found at {settings.CSV_FILE_PATH}")
        return

    print(f"Loaded {len(df)} destinations from CSV.")
    
    # Xử lý NaN (giá trị trống) trong các cột
    df = df.fillna('') # Thay thế NaN bằng chuỗi rỗng

    # 2. Tạo Corpus và Fit Vectorizer
    corpus = get_corpus(df)
    vectorizer = HybridVectorizer()
    vectorizer.fit(corpus) 
    
    documents_to_insert = []
    
    print("Generating vectors and documents...")
    for index, row in df.iterrows():
        #
        text_chunk = corpus[index] 
        hybrid_vector = vectorizer.transform_single(text_chunk) 
        
        # Lấy cột 'tag' từ CSV và tách nó thành một mảng (list)
        tags_from_csv = [tag.strip() for tag in row.get('tag', '').split(',') if tag.strip()]
        
        doc = {
            "landmark_id": row.get('name'), 
            "name": row.get('name'),
            "location": row.get('location'),
            "text_chunk": text_chunk, 
            "v_hybrid": hybrid_vector, 
            
            # --- Hard Filter Fields (Đã đơn giản hóa) ---
            "tags_array": tags_from_csv, 
            
            
            # Retrieval Fields
            "description": row.get('description'),
            "info_summary": row.get('description') 
        }
        
        documents_to_insert.append(doc)

    # 4. Nạp vào MongoDB
    if documents_to_insert:
        print(f"Inserting {len(documents_to_insert)} documents into MongoDB...")
        collection.delete_many({}) 
        collection.insert_many(documents_to_insert) 
        print("Ingestion complete.") 

if __name__ == "__main__":
    run_ingestion()