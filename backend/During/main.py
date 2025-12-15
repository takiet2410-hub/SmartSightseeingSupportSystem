from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import shared_resources
from visual_search import router as visual_search_router
# [NEW] Import router từ detection_history để có API sync
from detection_history import router as history_sync_router 
from history_detail import router as history_detail_router

# ------------------------------
# INIT APP
# ------------------------------
app = FastAPI(
    title="Smart Tourism AI API (Modular)",
    version="2.2.0", # Bump version
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

app.include_router(visual_search_router)
app.include_router(history_detail_router)
app.include_router(history_sync_router) # [NEW] Gắn router sync

@app.get("/")
def read_root():
    return {"status": "Running", "message": "Welcome to Smart Tourism API."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8002, reload=True)