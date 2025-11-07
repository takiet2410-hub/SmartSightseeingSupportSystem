# Rank Results And Return Top K

**Problem:** To rank the "candidate list" (from the Hard Filter) based on the user's "soft preferences" (vibe query), generate an intelligent response, and format the final Top 3 list for the output.

**Objectives:**
* **1. Retrieval:** To accurately find and retrieve the Top-K most semantically relevant chunks (context) from the *candidate list* that match the user's soft query.
* **2. Generation (RAG):** To use the retrieved context to instruct an LLM (Llama 3) to reason, select the final Top 3, and generate a coherent, human-like justification for each choice.
* **3. Formatting:** To parse the LLM's (potentially unstructured) response into a strict, standardized JSON object that the Frontend API expects.

---

## 1.0 (Component 1) Retrieval: Find the Most Similar Candidates

**Problem:** From the *allowed* candidate list, find the Top-K most semantically similar items to the user's vibe query.

* **1.1 Vectorize the User's Query**
    * `1.1.1` Write a function `get_hybrid_query_vector(query_text)`.
    * `1.1.2` This function must take the user's string (e.g., "quiet trekking").
    * `1.1.3` It must run the string through the **TF-IDF Vectorizer**.
    * `1.1.4` It must run the string through the **SentenceTransformer (e.g., multilingual-e5-base)**.
    * `1.1.5` It must concatenate the two vectors (`[ V_TFIDF ; V_ST ]`) to create the final `V_hybrid_query`.

* **1.2 Query the Vector Database (ChromaDB)**
    * `1.2.1` Write a function `retrieve_top_k_chunks(query_vector, allowed_ids_list, k)`.
    * `1.2.2` This function must query ChromaDB using the `V_hybrid_query` (from 1.1).
    * `1.2.3` **Crucially:** The query must use the **Metadata Filter** (`where={"landmark_id": {"$in": allowed_ids_list}}`) to *only* search within the candidates from the Hard Filter.
    * `1.2.4` The query must request `n_results=k` (e.g., k=5) to get the Top-K closest chunks.
    * `1.2.5` The function must return the `metadatas` (including `landmark_id`) of these Top-K chunks.

---

## 2.0 (Component 2) Generation: Use LLM to Reason (RAG)

**Problem:** Use the Top-K retrieved items as "context" for an LLM to select the *final* Top 3 and write the human-like justification.

* **2.1 Augment (Gather Context)**
    * `2.1.1` Write a function `get_context_from_ids(retrieved_ids)`.
    * `2.1.2` This function queries the **PostgreSQL** `Destinations` table.
    * `2.1.3` It fetches the full-text details (`name`, `info_summary`, `activity_tags`) for the `landmark_id`s retrieved in step 1.2.

* **2.2 Build the LLM Prompt**
    * `2.2.1` Write a function `build_rag_prompt(user_query, context_list)`.
    * `2.2.2` This function must construct a clear prompt template.
    * `2.2.3` The template must include the user's original `user_query` ("...quiet trekking...") and the "context" (the full-text details from 2.1).
    * `2.2.4` The prompt must explicitly instruct the LLM (e.g., Llama 3) to:
        * "Act as a travel expert."
        * "Select the Top 3 best matches from the provided context."
        * "Write a friendly justification for each choice."
        * "Format the output as a JSON object."

* **2.3 Call the LLM API**
    * `2.3.1` Write a function `call_llm_api(prompt)`.
    * `2.3.2` This function handles the API call to your LLM provider (e.g., Gemini, Replicate) and returns the text/JSON response.

---

## 3.0 (Component 3) Format: Create the Final Output

**Problem:** Convert the LLM's response into the clean, standardized JSON format that the Frontend API expects.

* **3.1 Parse the LLM Response**
    * `3.1.1` Write a function `parse_llm_response(llm_output)`.
    * `3.1.2` This function must safely handle the LLM's raw output (e.g., extract text from JSON, or parse a markdown string if the LLM doesn't return perfect JSON).
    * `3.1.3` It must identify the final Top 3 `landmark_id`s and their `justification` strings.

* **3.2 Build the Final API Response**
    * `3.2.1` Create the final JSON object (the "Ranked List") that matches the API contract defined for the Frontend.
    * `3.2.2` Return this JSON response from the main `POST /recommend` function.

---

# ⚙️ Technical & System Metrics

These metrics measure the internal health and efficiency of our Filter-then-Rank RAG pipeline (PostgreSQL + ChromaDB + LLM).

### Latency
* **Overall Latency:** Total time from the user hitting "Submit" (`POST /recommend`) to the Top 3 results being displayed.
    * **Goal:** `< 20 seconds`
* **Component Latency (P90):** Measuring the 90th percentile latency for each step to identify bottlenecks:
    * *Step 1 (Filter):* PostgreSQL query time.
    * *Step 2 (Rank):* ChromaDB query time.
    * *Step 3 (Generate):* LLM (Llama 3) API response time.

### Retrieval Quality 
* **Hit Rate:** In our test set, does the Top-5 context retrieved by ChromaDB *contain* the "correct" answer before it's sent to the LLM?
* **Mean Reciprocal Rank (MRR):** Measures the rank of the *first* correct item retrieved. A high MRR means our vector search (TF-IDF + ST) is ranking highly relevant items first.

### Generation Quality 
* **Faithfulness / Groundedness:** Does the LLM's `Justification Summary` *only* use information provided in the "context" (from Step 2), or does it "hallucinate" (fabricate) facts?
* **Answer Relevance:** Does the final Top 3 *actually* match the user's "vibe" query, or did the LLM get distracted by other factors in the context?
