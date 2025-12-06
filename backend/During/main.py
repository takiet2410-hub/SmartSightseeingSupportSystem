# main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import shared_resources # Import file chứa hàm load resources
from visual_searchhh import router as visual_search_router # Import Visual Search Router
from detection_history import router as history_router     # Import History Router

# ------------------------------
# INIT APP
# ------------------------------
app = FastAPI(
    title="Smart Tourism AI API (Modular)",
    version="2.1.0",
    # Chạy hàm load_resources khi app khởi động
    on_startup=[shared_resources.load_resources] 
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------------
# ATTACH ROUTERS
# ------------------------------

# Gắn Router từ visual_search.py
app.include_router(visual_search_router)

# Gắn Router từ detection_history.py
app.include_router(history_router)

@app.get("/")
def read_root():
    return {"status": "Running", "message": "Welcome to Smart Tourism API. Go to /docs for API documentation."}
