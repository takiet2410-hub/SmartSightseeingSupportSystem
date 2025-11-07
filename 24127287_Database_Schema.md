# Database Design & Implementation: Decomposition

This document breaks down the complex problem of "Designing the Hybrid Database Schema" into smaller, manageable sub-problems, based on the project's architecture (PostgreSQL + ChromaDB + RAG).
This is a **"Filter-then-Rank"** architecture. It uses **PostgreSQL** for Hard Filtering and **ChromaDB + LLM** for Soft Ranking, following a RAG (Retrieval-Augmented Generation) pattern.

**Architecture Overview:**

- **PostgreSQL (Application DB):** The single source of truth for all structured, factual data (landmark details, user data).
    
- **ChromaDB (Search Index):** Used as two _separate_ indexes (Collections).
    
    1. `destination_texts`: For "Before" phase text search (RAG).
        
    2. `landmark_images`: For "During" phase image search.

---
# **The Flow**
## 1. 📥 Input: The User's Request

The user interacts with the Frontend and provides two types of data simultaneously:

- **Hard Constraints:** Selected from **Dropdowns/Checkboxes** (e.g., `Budget` = "Medium", `Specific Needs` = "Wheelchair").
    
- **Soft Preferences:** Typed freely into a **Text Box** (e.g., "I want a quiet, romantic place to 'heal'").
    

---

## 2. ⚙️ Step 1: The Hard Filter

- **Tool:** **PostgreSQL** (Relational Database)
    
- **Objective:** To rapidly eliminate all destinations that do not meet the binary YES/NO requirements.
    
- **Action:**
    
    1. The Backend API (FastAPI) receives the request.
        
    2. It queries the **PostgreSQL** (`Destinations` table) to get a list of `landmark_id`s that _exactly_ match the Hard Constraints.
        
    3. **Example Query (Logic):** `SELECT landmark_id FROM Destinations WHERE budget_range = 'Medium' AND specific_needs_tags LIKE '%Wheelchair%';`
        
- **Result:** A short-list of valid "candidates" (e.g., 20 `allowed_ids`).
    

---

## 3. 🧠 Step 2: The Soft Rank (Retrieval)

- **Tool:** **Vector Database (ChromaDB)**
    
- **Objective:** To rank the 20 "candidates" (from Step 1) based on their _similarity_ to the Soft Preference (the "vibe").
    
- **Action:**
    
    1. The Backend API (FastAPI) takes the user's "vibe" string ("...quiet...heal...") and converts it into a **Hybrid Vector** (`V_hybrid_query`) of 5384 dimensions (using your team's **TF-IDF + SentenceTransformer** pipeline).
        
    2. It performs a "Hybrid Search" query against **ChromaDB**.
        
    3. **Example Query (Logic):** "Find the Top 5 vectors (Cosine Similarity) closest to `V_hybrid_query` **ON THE CONDITION (WHERE)** the `landmark_id` is in the list of 20 `allowed_ids` from Step 1."
        
- **Result:** A very short list (e.g., Top 5 `retrieved_ids`) of the most relevant destinations.
    

---

## 4. ✍️ Step 3: Generation & Synthesis (RAG)

- **Tool:** **LLM (Meta Llama 3 / Gemini)** and **PostgreSQL**
    
- **Objective:** To turn the Top 5 "robotic" results (from Step 2) into an intelligent, human-like answer.
    
- **Action:**
    
    1. **Augmentation:** The Backend API takes the 5 `retrieved_ids` and queries **PostgreSQL** again to get their full details (name, `info_summary`, `activity_tags`...).
        
    2. **Generation:** The Backend API "stuffs" these details into a prompt for the **LLM**, serving as "context".
        
    3. **Example Prompt (Logic):** "You are a travel expert. The user wants 'a quiet place to heal'. Based on these 5 relevant locations: [Data for location A...], [Data for location B...], please select the Top 3 best choices and write a friendly 'Justification Summary' for each."
        
- **Result:** The LLM reasons upon the context and returns a final answer (Top 3 + Justification).
    

---

## 5. 📤 Output: The Final Response

- The Backend API (FastAPI) formats the LLM's response into a standard JSON.
    
- The Frontend receives the JSON and displays the final Top 3 recommendations (with the intelligent justification) to the user.
---
# **Work Breakdown Tree**
## 1.0 PostgreSQL: The Relational (Application) Database

**Problem:** Storing and filtering all structured, "factual" data (Hard Constraints).

* **1.1 Define Schema (The "Blueprint")**
    *   1.1.1 `Destinations` Table: This is the **single source of truth** for all landmark details.
        
        - `landmark_id` (Primary Key, e.g., INT or VARCHAR from Google Landmarks)
        - `name` (TEXT) - (Used by "Before" & "During")
        - `location_province` (VARCHAR) - (Used by "Before")
        - `budget_range` (VARCHAR, e.g., 'Low', 'Medium', 'High') - (Used by "Before")
        - `companion_tags` (TEXT or ARRAY[TEXT]) - (Used by "Before")
        - `specific_needs_tags` (TEXT or ARRAY[TEXT]) - (Used by "Before")
        - `info_summary` (TEXT) - (Source for "Before" vector, Used by "During" output)
        - `vibe_tags` (TEXT) - (Source for "Before" vector)
        - `activity_tags` (TEXT) - (Source for "Before" vector)
        - `overall_rating` (FLOAT) - (Used by "Before")
        - `actionable_advice` (TEXT) - (Used by "Before" & "During" output)
        - `google_mid` (VARCHAR UNIQUE) - (Used by during)
    - 1.1.2 `Users` Table: Design for user accounts (if login is needed).
        - `user_id` (Primary Key)
        - `email`, `password_hash`
    - 1.1.3 `User_Saved_Destinations` Table: Design a "join table" to link users to destinations.
        - `user_id` (Foreign Key)
        - `landmark_id` (Foreign Key)
- **1.2 Implement & Populate*
    - 1.2.1 Write the `CREATE TABLE` SQL scripts for the schemas defined in 1.1.
    - 1.2.2 Write a Python "Ingestion" Script (using `psycopg2` or `SQLAlchemy`):
        - Task: Read the `destinations_database.csv` spreadsheet (for "Before").
        - Task: Loop through each row and `INSERT` it into the `Destinations` table.

---

## 2.0 Data Pre-processing (The "Chunking" Problem)

**Problem:** Raw text from the database (`info_summary`, `vibe_tags`, ...) is too large to be fed into an embedding model effectively. A single vector for a 1000-word text will be "diluted" and cannot represent any specific meaning. We must chunk the text into meaningful segments to prepare for the RAG (Retrieval-Augmented Generation) pipeline.

---

- **2.1 Define Text Corpus**
    
    - 2.1.1 `Function: get_corpus(destination)`: Write a function that takes a destination (e.g., a row from PostgreSQL) and combines all "soft fields" (`info_summary`, `vibe_tags`, `activity_tags`) into a single large text string.
        
        - **Output Example:** `"UNESCO world heritage... Historic;Quiet;Romantic... Cuisine;Culture;Photography..."`
            

---

- **2.2 Define Chunking Strategy**
    
    - 2.2.1 Select a Semantic Text Splitter: Decide on a splitter that prioritizes semantics.
        
        - **Tool:** `RecursiveCharacterTextSplitter` (from LangChain).
            
        - **Why:** It attempts to split intelligently, prioritizing separators in order: `\n\n` (double newline), `\n` (newline), `.` (punctuation), and then (space). This helps keep sentences/paragraphs intact.
            
    - 2.2.2 Define `chunk_size`: Decide the maximum size for each chunk.
        
        - **Tool:** `chunk_size = 512` (tokens or characters).
            
        - **Why:** This is a balance. It's small enough for the resulting vector to be _specific_, but large enough to contain _context_.
            
    - 2.2.3 Define `chunk_overlap`: Decide how many tokens/characters each new chunk will "borrow" from the end of the previous chunk.
        
        - **Tool:** `chunk_overlap = 50` (tokens or characters).
            
        - **Why (Your Core Reason):** This is extremely important to **preserve semantic context** when an important sentence is cut between two chunks.
            
        
        **Example of Overlap's Importance:**
        
        - **Original Text:** "...This location is very quiet. It is the perfect place to heal your soul..."
            
        - **Chunking (NO Overlap):**
            
            - _Chunk 1:_ "...This location is very quiet."
                
            - _Chunk 2:_ "It is the perfect place to heal your soul..."
                
            - _Problem:_ If a user searches for "quiet place to heal," the system might only find Chunk 2 (because of "heal") but lose the "quiet" context from Chunk 1.
                
        - **Chunking (WITH 50-char Overlap):**
            
            - _Chunk 1:_ "...This location is very **quiet. It is the perfect** place..."
                
            - _Chunk 2:_ "...**quiet. It is the perfect** place to heal your soul..."
                
            - _Result:_ Both chunks now contain the "quiet" and "heal" semantics, making retrieval much more accurate.
                

---

- **2.3 Execute Ingestion Pipeline**
    
    - 2.3.1 `Script: run_ingestion()`: Write a main script that runs _once_ to prepare the Vector DB (ChromaDB).
        
    - 2.3.2 Loop & Process: This script will: a. `SELECT * FROM Destinations` from PostgreSQL. b. Loop through each destination. c. Get the raw text (from 2.1.1). d. Apply the chunking strategy (from 2.2) to create (for example) 5 chunks from 1 destination.
        
    - 2.3.3 Store Chunks with Metadata (Crucial):
        
        - When saving these chunks to ChromaDB (WBS 3.3), **each chunk** must be stored with the **Metadata** of its "parent" destination.
            
        - **Example (Saving Chunk 1 for Hoi An):**
            
            - **Vector:** `V_hybrid` of (Chunk 1)
                
            - **Metadata:** `{ "landmark_id": 12345, "budget_range": "Medium", "specific_needs": ["Wheelchair"] }`
                
            - **ID:** `12345_chunk_1`
                
        - **Why:** This ensures that when Step 1 (Hard Filter) returns `landmark_id = 12345`, Step 2 (Soft Rank) can find _all_ chunks (`12345_chunk_1`, `12345_chunk_2`...) that belong to that destination.

---

## 3.0 ChromaDB: The Vector (Search Index) Database

**Problem:** Storing, indexing, and retrieving two _different types_ of vectors (Text and Image) based on similarity.

* **3.1 Setup ChromaDB**
    * 3.1.1 `pip install chromadb`
    * 3.1.2 Initialize the client (e.g., Persistent Mode to save data).
    * 3.1.3 Create a "Collection" (e.g., `destination_chunks`) to store the vectors.
    * 3.1.4 Create Collection 2 (Module "During"): `landmark_images`

* **3.2 Define the Hybrid Vector Pipeline** (Module Before)
    * 3.2.1 Implement the **TF-IDF Vectorizer**:
        * Task: `fit` the vectorizer on the *entire* text corpus (all chunks) to build its vocabulary.
    * 3.2.2 Implement the **SentenceTransformer (ST) Loader**:
        * Task: Load the pre-trained model (e.g., `multilingual-e5-base`).
    * 3.2.3 Write the `create_hybrid_vector` function:
        * Input: A single text chunk.
        * Output: `V_hybrid = [ V_TFIDF(chunk) ; V_ST(chunk) ]` (the 5384-dim vector).

* **3.3 Storing Vectors (Ingestion)** (Module Before)
    * 3.3.1 Write a script to loop through every chunk (from 2.3).
    * 3.3.2 For each chunk, generate its `V_hybrid` (using 3.2.3).
    * 3.3.3 For each chunk, retrieve its "Hard Constraint" data from PostgreSQL (Budget, Needs, etc.).
    * 3.3.4 Add the data to ChromaDB:
        * `collection.add(`
        * `embeddings=[ V_hybrid ],`
        * `metadatas=[{ "landmark_id": ..., "budget_range": ..., "specific_needs": ... }],`
        * `ids=[ unique_chunk_id ]`
        * `)`

* **3.4 Vector Indexing**
    * 3.4.1 This is handled *automatically* by ChromaDB (it uses an HNSW index).
    * 3.4.2 Confirm the distance metric: The default is Cosine Similarity, which matches your pipeline's plan. No action is needed other than verification.
- **3.5 Module "During" Image Vector Ingestion**
    
    - **Problem:** Store vector representations of all images from `VN_train.csv` for fast similarity search.
    - `3.5.1` Define Image Vectorizer: Select or train the CV model (e.g., from Roboflow, or a standard like EfficientNet/DELF) that turns an image into a vector.
    - `3.5.2` Write a _new_ ingestion script: `ingest_image_data()`.
    - `3.5.3` Loop & Process: This script reads `VN_train.csv` row by row.
    - `3.5.4` Vectorize: For each row, it must (a) download the image from the `url` and (b) pass the image through the Image Vectorizer (3.5.1) to get an `image_vector`.
    - `3.5.5` Store in ChromaDB: Add the vector to the **`landmark_images`** collection:
        - `collection.add(`
        - `embeddings=[ image_vector ],`
        - `metadatas=[{ "landmark_id": row.landmark_id, "image_id": row.id }],`
        - `ids=[ row.id ]`
        - `)`

---

## 4.0 Information Retrieval (The Hybrid Query Pipeline)

**Problem:** Combining the two databases to answer a user's query in a unified, two-step process.

* **4.1 Step 1: Hard Filter (WBS 2.1)**
    * 4.1.1 Write the `get_filtered_ids` function (Python/FastAPI).
    * 4.1.2 Input: User's Hard Constraints (e.g., `budget="Medium"`, `needs="Wheelchair"`).
    * 4.1.3 Action: Query the **PostgreSQL** `Destinations` table (`SELECT landmark_id WHERE...`).
    * 4.1.4 Output: A list of *allowed* `landmark_id`s (e.g., `[id_A, id_B, id_C]`).

* **4.2 Step 2: Soft Ranking (WBS 2.2)**
    * 4.2.1 Write the `get_ranked_results` function (Python/FastAPI).
    * 4.2.2 Input: User's Soft query (e.g., "quiet trekking") and the `allowed_ids` list from 4.1.
    * 4.2.3 Action 1: Generate the `V_hybrid_query` for the user's text.
    * 4.2.4 Action 2: Query **ChromaDB** using **Metadata Filtering**:
        * `collection.query(`
        * `query_embeddings=[ V_hybrid_query ],`
        * `n_results=K,`
        * `where={"landmark_id": {"$in": allowed_ids}}`
        * `)`

* **4.3 Step 3: Define Score Threshold**
    * 4.3.1 Analyze the (cosine) distances/scores returned by ChromaDB queries.
    * 4.3.2 Implement a rule: `if score < 0.75: discard_result`. This prevents irrelevant (but "closest") results from being shown.

* **4.4 Step 4: Augmentation & Generation (RAG)**
    * 4.4.1 Take the Top-K results from 4.2.
    * 4.4.2 Retrieve their full `info_summary` from **PostgreSQL**.
    * 4.4.3 Format these summaries as "Context" and build the prompt for the LLM (Llama 3).
    * 4.4.4 Write the function to call the LLM API and return the final answer.


