## Decomposition: Finalize API Endpoint: POST /create-album

Problem:

To build a single API endpoint that can receive a batch of uploaded image files, orchestrate the complex processing pipeline (Metadata Extractor -> Filtering/Clustering/Curation Logic), and format the final, organized "story" JSON to send back to the user.

**Objectives:**

- **1. Integration:** Ensure the data (`list` of `PhotoObject`s) flows correctly and sequentially through the Extraction (4.1), Filtering (4.2), Clustering (4.3), and Curation (4.4) modules.
    
- **2. Formatting:** Construct a single, logical, nested JSON output that is easy for the Frontend to parse and render (e.g., grouped by Day, then by Scene).
    
- **3. Performance & Cleanup:** Securely process temporary files and ensure they are deleted after the request is complete, even if an error occurs, to prevent server disk overflow.
    

## 🛠️ Tools & Libraries

|**Category**|**Tool / Library**|**Purpose**|
|---|---|---|
|**API Framework**|`FastAPI`|To build the `POST /create-album` endpoint.|
|**File Handling**|`typing.List`, `UploadFile`, `File`|To handle the batch file upload.|
|**Temp Files**|`tempfile`, `shutil`|To save the uploaded files securely on the server.|
|**Module 4.1**|`exifread`, `os`|(Called by API) To extract `timestamp` and `gps`.|
|**Module 4.2**|`hashlib`, `TensorFlow/Keras`, `OpenCV`|(Called by API) To filter duplicates, screenshots, and bursts.|
|**Module 4.3**|`sklearn.cluster.DBSCAN`, `geopy`|(Called by API) To create Day and GPS clusters.|
|**Module 4.4**|`OpenCV` (for `blur_score`), `max()`|(Called by API) To compare scores and select the `best_shot`.|

---

## Breakdown of Sub-Problems

###  4.5.0: Component 0: Build API Endpoint & Handle Ingestion


**Problem:** How to receive _multiple_ files from the user and save them securely for processing.

- **Decomposition:**
    
    - **4.5.0.1: Define API Route:**
        
        - **Tool:** `FastAPI`
            
        - **Action:** Define the main API controller function and register its route: `@app.post("/create-album")`.
            
    - **4.5.0.2: Handle Batch Upload:**
        
        - **Tool:** `FastAPI`, `typing`
            
        - **Action:** Define the function's input parameter to accept a list of files: `async def create_album(files: List[UploadFile] = File(...))`.
            
    - **4.5.0.3: Save Temporary Files:**
        
        - **Tool:** `tempfile`, `shutil`
            
        - **Action:** Write a loop that iterates through the `files`, creates a secure temporary directory (`temp_dir = tempfile.mkdtemp()`), and saves each file to that directory, returning a list of `temp_file_paths`.
            

---

### 4.5.1: Component 1: Pipeline Integration


**Problem:** To orchestrate the flow of data sequentially, where the output of one module becomes the input for the next.

- **Decomposition:**
    
    - **4.5.1.1: Call Module 4.1 (Metadata Extraction):**
        
        - **Action:** Call the `process_image_batch(temp_file_paths)` and `apply_missing_data_logic()` functions (defined in WBS 4.1).
            
        - **Input:** The `list_of_temp_paths` (from 4.5.0.3).
            
        - **Output:** `final_photo_list` (a `list` of `PhotoObject`s now containing `timestamp` and `gps`).
            
    - **4.5.1.2: Call Module 4.2 (Junk Filtering):**
        
        - **Action:** Call the `filter_junk_photos(final_photo_list)` function (defined in WBS 4.2).
            
        - **Input:** `final_photo_list` (from 4.5.1.1).
            
        - **Output:** `clean_list` (a _filtered_ `list` of `PhotoObject`s).
            
    - **4.5.1.3: Call Module 4.3 (Clustering):**
        
        - **Action:** Call the `cluster_by_day(clean_list)`, `cluster_by_gps(clean_list)`, and `get_cluster_names(...)` functions (defined in WBS 4.3).
            
        - **Input:** `clean_list` (from 4.5.1.2).
            
        - **Output (3 separate variables):**
            
            1. `day_clusters`: (e.g., `{"Day 1": [...], "Day 2": [...]}`)
                
            2. `clean_list_with_clusters`: (The `clean_list` but with `cluster_id` updated on each object)
                
            3. `cluster_name_map`: (e.g., `{0: "Notre Dame Cathedral", 1: "Museum..."}`)
                
    - **4.5.1.4: Call Module 4.4 (Curation):**
        
        - **Action:** Call the `select_best_shots(day_clusters, clean_list_with_clusters)` function (defined in WBS 4.4).
            
        - **Input:** The outputs from 4.5.1.3.
            
        - **Output:** `best_shots_map` (e.g., `{"Day 1_cover": imgA, "cluster_0_cover": imgB, ...}`)
            

---

###  4.5.2: Component 2: Format JSON Output


**Problem:** To assemble all the disconnected pieces of data from Component 1 into a single, structured "story" JSON.

- **Decomposition:**
    
    - **4.5.2.1: Write a function to build the `Trip Summary`:**
        
        - **Action:** Get data from `day_clusters` and `clean_list`.
            
        - **Output (JSON):**
            
            JSON
            
            ```
            "trip_summary": {
              "total_days": 2,
              "photos_kept": 250,
              "start_date": "2025-10-30",
              "end_date": "2025-10-31"
            }
            ```
            
    - **4.5.2.2: Write the Nested JSON Builder function:**
        
        - **Action:** This is the most complex function. It must loop through `day_clusters` (e.g., "Day 1").
            
        - **Inside** each day, it must group that day's photos by their `cluster_id` (from `clean_list_with_clusters`).
            
        - It must look up the `cluster_name_map` to get the scene name.
            
        - It must look up the `best_shots_map` to get the cover photos.
            
    - **4.5.2.3: Assemble the Final JSON:**
        
        - **Action:** Combine the outputs of 4.5.2.1 and 4.5.2.2 into the final object.
            
        - **Output (Example JSON):**
            
            JSON
            
            ```
            {
              "trip_summary": { ... },
              "album_structure": [
                {
                  "day": "Day 1",
                  "cover_photo_id": "imgA_id",
                  "scenes": [
                    {
                      "cluster_id": 0,
                      "cluster_name": "Notre Dame Cathedral",
                      "cover_photo_id": "imgB_id",
                      "photos": [ ... (list of photo objects) ... ]
                    },
                    {
                      "cluster_id": 1,
                      "cluster_name": "War Remnants Museum",
                      "cover_photo_id": "imgC_id",
                      "photos": [ ... ]
                    }
                  ]
                },
                { "day": "Day 2", ... }
              ]
            }
            ```
            

---

###  4.5.3: Component 3: Cleanup & Response


**Problem:** To ensure the temporary files (which could be gigabytes) are deleted, even if the pipeline fails.

- **Decomposition:**
    
    - **4.5.3.1: Implement `try...finally` Block:**
        
        - **Action:** Wrap Component 1 (4.5.1), Component 2 (4.5.2), and Component 3 (4.5.3) inside a `try` block.
            
    - **4.5.3.2: Write Cleanup Function:**
        
        - **Tool:** `shutil`
            
        - **Action:** Place the cleanup logic inside the `finally` block.
            
        - **Code (logic):** `shutil.rmtree(temp_dir)` (This deletes the temporary directory and all files inside it).
            
    - **4.5.3.3: Return HTTP Response:**
        
        - **Action:** If the `try` block succeeds, return the final JSON (from 4.5.2.3) with an `HTTP 200 OK`.
            
        - **Action:** If the `try` block fails (in an `except` block), log the error and return an `HTTP 500 Internal Server Error`.