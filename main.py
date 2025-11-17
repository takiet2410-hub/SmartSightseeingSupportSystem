from fastapi import FastAPI, HTTPException, Depends
from schemas import RecommendationRequest, RecommendationResponse
from modules.vectorizer import HybridVectorizer
from modules.retrieval import retrieve_context
from modules.generation import build_rag_prompt, call_llm_api, parse_llm_response
from core.config import settings
from contextlib import asynccontextmanager

# Khởi tạo vectorizer toàn cục
vectorizer = HybridVectorizer()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load model khi server khởi động
    print("Loading models...")
    vectorizer.load_fitted_tfidf(settings.VECTORIZER_PATH)
    print("Models loaded.")
    yield
    # (Clean up)
    
app = FastAPI(
    title="Smart Tourism System - 'Before' Module",
    lifespan=lifespan
)

@app.get("/")
def read_root():
    return {"message": "Welcome to the Smart Tourism 'Before' Module API"}

@app.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(request: RecommendationRequest):
    try:
        # ---Vectorize the User's Query---
        print(f"Received query: {request.vibe_prompt}")
        query_vector = vectorizer.transform_single(request.vibe_prompt)
        
        # ---Implement Hybrid Search (Retrieval)---
        
        retrieved_context = retrieve_context(request.hard_constraints, query_vector)
        
        if not retrieved_context:
            return RecommendationResponse(status="error", recommendations=[], debug_info={"message": "No destinations found matching criteria."})

        # ---Implement Output Generation (RAG) ---
        
        # Augment (Gather Context)
        context_str = "\n\n".join([str(doc) for doc in retrieved_context])
        
        # Build the LLM Prompt
        prompt = build_rag_prompt(context=context_str, user_query=request.vibe_prompt)
        
        # Call the LLM API
        llm_raw_response = call_llm_api(prompt)
        
        # Format the Final Output
        parsed_response = parse_llm_response(llm_raw_response)
        
        if "error" in parsed_response:
             raise HTTPException(status_code=500, detail=parsed_response["error"])

        return RecommendationResponse(
            status="success",
            recommendations=parsed_response.get("recommendations", []),
            debug_info={"retrieved_count": len(retrieved_context), "top_match_score": retrieved_context[0].get('score')}
        )

    except Exception as e:
        print(f"An error occurred: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    # Chạy server
    # uvicorn main:app --reload
    print("Run the server using: uvicorn main:app --reload")