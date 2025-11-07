# Landmarks Information Retrieval Logic : Decomposition

Problem:

The Google Vision AI (WBS 3.2) returns technical data (a description string and a mid string). We must reliably link this data to our internal PostgreSQL database to fetch the rich, human-readable content (summary, tips, etc.) that the user actually wants to see.

**Objectives:**

- **1. Reliable Linking:** To establish a 100% accurate, high-speed link between the Google Vision AI `mid` (Machine-Generated ID) and the corresponding `landmark_id` in our PostgreSQL database, avoiding fragile string matching.
    
- **2. Contextual Validation (Optional):** To intelligently use the _best available_ GPS data (from the photo's EXIF, or the device's live location) as an optional "hint" to validate the match, without incorrectly failing the "At-Home" use case.
    
- **3. Content Retrieval:** To fetch the curated, human-readable content from PostgreSQL to display to the user.
    

---

### 3.3.1 Component 1: Schema Preparation (One-Time Setup)

🎯 **Objective:** To create the "bridge" in our PostgreSQL database that allows Google's `mid` to connect to our internal `landmark_id`.

- **Problem:** Our `Destinations` table (from Module "Before") has no knowledge of Google's internal IDs.
    
- **Decomposition:**
    
    - **3.3.1.1: Modify `Destinations` Table Schema (WBS 1.1.1):**
        
        - Action: Add a new, unique column to the `Destinations` table in PostgreSQL.
            
        - **SQL:** `ALTER TABLE Destinations ADD COLUMN google_mid VARCHAR(255) UNIQUE;`
            
    - **3.3.1.2: Populate the `google_mid` Column (Data Ingestion):**
        
        - Action: For each landmark in your `destinations_database.csv`, manually find its Google Knowledge Graph `mid` (e.g., "Notre-Dame Cathedral Saigon" $\rightarrow$ `/m/026kv_`).
            
        - Action: Add this `mid` to the spreadsheet, so it is loaded into the PostgreSQL database along with all other data (WBS 1.2.2).
            
        - **Result:** Your `Destinations` table now has the linking key.
            

---

### 3.3.2 Component 2: Process CV API Response (WBS 3.2.2)

🎯 **Objective:** To extract the crucial `mid` (the key) from the Google Vision AI JSON, not just the description.

- **Problem:** The default JSON response contains many fields. We must parse it correctly.
    
- **Decomposition:**
    
    - **3.3.2.1: Write JSON Parsing Function:**
        
        - Write a function `parse_google_vision_response(json_response)`.
            
    - **3.3.2.2: Extract Key Information:**
        
        - This function must extract:
            
            - `landmark_name = response["landmarkAnnotations"][0]["description"]`
                
            - `confidence = response["landmarkAnnotations"][0]["score"]`
                
            - **`google_mid = response["landmarkAnnotations"][0]["mid"]` (The most important part)**
                
    - **Output:** A clean object: `{ "landmark_name": "...", "confidence": 0.98, "google_mid": "/m/026kv_" }`
        

---

### 3.3.3 Component 3: Contextual Validation (Optional Step)

🎯 **Objective:** To intelligently validate the CV match using the _best available_ GPS data, without incorrectly failing the "At-Home" use case.

- **Problem:** The user might be in Hanoi uploading a photo from Saigon. A simple GPS check will fail.
    
- **Decomposition:**
    
    - **3.3.3.1: Get All Contextual Inputs:**
        
        - Input 1: The `google_mid` (from 3.3.2).
            
        - Input 2: `user_upload_method` (e.g., `"CAMERA_SCAN"` vs `"GALLERY_UPLOAD"`).
            
        - Input 3: `user_current_gps` (Device's live GPS).
            
        - Input 4: `photo_exif_gps` (GPS from the photo's metadata, if available).
            
    - **3.3.3.2: Determine Validation GPS Source:**
        
        - Implement logic to find the _best_ GPS source:
            
            - **Priority 1 (Best):** Use `photo_exif_gps` if it exists.
                
            - **Priority 2 (On-the-Spot):** Use `user_current_gps` _only if_ `user_upload_method == "CAMERA_SCAN"`.
                
            - **Priority 3 (Skip):** If neither is available, `validation_gps = None`.
                
    - **3.3.3.3: Execute Optional Validation Rule:**
        
        - **Only run if `validation_gps is not None`:**
            
        - a. Fetch the landmark's true location (`landmark_gps`) from PostgreSQL using the `google_mid`.
            
        - b. Calculate the `distance` between `validation_gps` and `landmark_gps`.
            
        - c. `if distance > VALIDATION_RADIUS (e.g., 10 km):`
            
            - `validation_status = "Warning: Mismatch"`
                
        - `else:`
            
            - `validation_status = "Verified"`
                

---

###  3.3.4 Component 4: Final Information Retrieval (The Core Task)

🎯 **Objective:** To fetch the curated, human-readable content from PostgreSQL using the reliable `google_mid`.

- **Problem:** The user needs the rich content (summary, tips) from our database, not Google's.
    
- **Decomposition:**
    
    - **3.3.4.1: Write Final Retrieval Function:**
        
        - Write a function `get_destination_details(google_mid)`.
            
    - **3.3.4.2: Query PostgreSQL (The "Source of Truth"):**
        
        - This function **must** query the `Destinations` table using the `google_mid`, _not_ the landmark name.
            
        - **Example Query:**
            
            SQL
            
            ```
            SELECT name, info_summary, actionable_advice, overall_rating
            FROM Destinations
            WHERE google_mid = [retrieved_google_mid];
            ```
            
    - **3.3.4.3: Format Output JSON:**
        
        - Take the result from the SQL query (which will be in your preferred language, e.g., "Nhà thờ Đức Bà Sài Gòn").
            
        - Add the `validation_status` (from 3.3.3) for the UI.
            
        - Return this final, user-friendly JSON to the Frontend.