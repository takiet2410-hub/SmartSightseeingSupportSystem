
    npm install
    # or
    yarn install
    ```
    
3. Configure Environment:
    
    - Create `.env` file.
        
    - Set API Base URLs:
        
        Code snippet
        
        ```
        VITE_AUTH_API=http://localhost:8001
        VITE_BEFORE_API=http://localhost:8002
        VITE_DURING_API=http://localhost:8000
        VITE_AFTER_API=http://localhost:8003
        ```
        
4. **Start Application:**
    
    Bash
    
    ```
    npm run dev
    ```
    
5. Open browser at `http://localhost:3000` (or the port shown in terminal).
    
---

## 📝 Testing Flow for Evaluators

To test the complete flow of the system:

1. **Start all 4 Backend Servers** and the **Frontend** in separate terminals.
    
2. **Open the Frontend** in your browser.
    
3. **Registration/Login:** Create an account (Hits **Auth Service**).
    
4. **Search Places or Get Recommendation:** Find a place to travel (Hits **Before Service**).
    
5. **Visual Search:** Upload an image of a landmark (Hits **During Service**).
    
6. **Create Album:** Create Albums and Trip Summary based on the pictures you take (Hits **After Service**).

---
