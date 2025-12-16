# "Before" Backend Unit Testing 
This document outlines the Testing Strategy, structure, and instructions for executing Unit Tests for the Travel Recommendation Backend (FastAPI).
## 1. Testing Strategy Overview
The system uses pytest as the primary framework. The goal is to validate business logic in isolation, ensuring no dependencies on external services during testing.
+ Comprehensive Mocking:
   + Database (MongoDB): No real DB connections. We use unittest.mock to simulate collection.find, insert, and update operations.
   + AI/ML Models: HybridVectorizer and LLM APIs (Gemini/OpenAI) are mocked to prevent heavy model loading, avoid token costs, and ensure fast execution.
   + Authentication: The get_current_user dependency is overridden to bypass complex login flows.
+ Fail-safe & Resilience Testing: Validates the system's ability to handle faults gracefully when third-party APIs (Weather, Auth Server) timeout or return malformed data.
## 2. Environment Setup
Ensure the necessary testing libraries are installed:
```Bash
pip install pytest pytest-cov httpx
```

## 3. Test Suite Structure
| File Name | Scope | Details |
| :--- | :--- | :--- |
| **`conftest.py`** | Configuration | Sets up `TestClient`, Mocks Auth (always returns "test_user_123"), and Mocks Vectorizer (prevents heavy AI loads). |
| **`test_destinations.py`** | Core Feature | Tests destination retrieval, filtering, pagination, and detail views with weather integration. |
| **`test_generation.py`** | AI & RAG | Validates Semantic Search and Recommendation flows. Checks the integration of Vector Search results with LLM responses. |
| **`test_retrieval.py`** | Data Logic | Tests MongoDB query construction (`build_filter_query`) and "Dirty Data" handling (Null safety). |
| **`test_favorite.py`** | User Action | Tests Add/Remove favorites functionality and handles 404 cases for invalid landmarks. |
| **`test_external.py`** | Edge Cases | **Critical:** Tests error handling when External APIs (Weather, LLM, Auth Proxy) timeout or return 503 errors. |
| **`test_utils.py`** | Utilities | Unit tests for utility functions: Vietnamese sorting, keyword normalization, and tag string processing. |
## 4. Running the Tests
1. Run all tests
```Bash
pytest
```
2. Run with Coverage Report
To ensure all logic branches are covered:
```Bash
pytest --cov=. --cov-report=term-missing
```
3. Run a specific file (e.g., AI tests)
```Bash
pytest test_generation.py
```
## 5. Key Testing Scenarios
The following critical logic is strictly protected by tests:
1. Data Safety: The system must not crash if the Database returns missing fields (e.g., image_urls or overall_rating is None) → Verified in test_retrieval.py.
2. Graceful Degradation: If the Weather API times out, the Destination Details API must still return the destination data (with weather: null) instead of a 500 error → Verified in text_external.py.
3. Vietnamese Locale Sorting: Ensures accurate sorting where "D" comes before "Đ" (Correct Vietnamese collation vs. standard ASCII) → Verified in test_utils.py.