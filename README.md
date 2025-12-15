
---

# Smart Sightseeing Support System

Welcome to the **Smart Sightseeing Support System**. This project utilizes a **Microservices-based Architecture** to provide a comprehensive tourism experience. The system is divided into 5 independent modules (4 Backend Services & 1 Frontend Application) to manage different stages of the user journey:

1. **Auth Service:** Manages User Authentication & Authorization.
    
2. **Before Service:** "AI Travel Consultant".
    
3. **During Service:**  Sightseeing Landmarks recognition and history.
    
4. **After Service:** "Your_After_Feature_Here".
    
5. **Frontend:** The user interface connecting all services.
    

---

## 🛠 General Prerequisites

Before running any service, ensure you have the following installed globally:

- **Python 3.10+** (Developed on 3.10.19)
    
- **Node.js & npm/yarn** (for Frontend)
    
- **MongoDB Atlas Account**
    
- **Cloudinary Account**
    
- **Brevo Account** (for mail sending)
    
- **Git**
    

---

# 🚀 Installation & Execution Guide

This project uses **Git LFS (Large File Storage)** to handle large AI model files (>100MB). Please read the instructions below carefully to ensure you download the full source code and model files correctly.

---

### ⚠️ IMPORTANT WARNING

1.  **DO NOT USE THE "DOWNLOAD ZIP" BUTTON** on GitHub. This method often fails to download the actual LFS files (you will likely end up with 1KB pointer files instead).
2.  You must use `git clone` and have `git lfs` installed.

---

### 🛠️ Prerequisites

Before downloading the code, ensure your machine has the following installed:
1.  [Git](https://git-scm.com/downloads)
2.  **Git LFS**:
    * **Windows:** Download and install from [git-lfs.com](https://git-lfs.com) (or run `git lfs install` in Git Bash if you have the latest Git version).
    * **Mac/Linux:** Run the command `git lfs install`.

---

### 📥 Installation & Cloning

Follow these steps in order to ensure no files are missing.

#### Step 1: Activate Git LFS
Open your Terminal (CMD or Git Bash) and run the following command to ensure LFS is enabled:

```bash
git lfs install
````

#### Step 2: Clone the Repository

Run the standard clone command:

Bash

```
git clone [PASTE YOUR GITHUB REPO LINK HERE]
```

#### Step 3: Navigate to Project Directory

Bash

```
cd [YOUR PROJECT FOLDER NAME]
```

#### Step 4: Pull Model Files (Crucial Step)

Usually, Git pulls LFS files automatically during cloning. However, to guarantee you have the actual model file (approx. 500MB) instead of the pointer file (1KB), run:

Bash

```
git lfs pull
```

_Note: This process may take a few minutes depending on your internet speed._

---
## Since the backend services run independently, you will need to open **multiple terminal tabs** to keep all services running simultaneously.

Please follow the instructions for each module below.

---------
## 1. Auth Service (Authentication)

_Handles registration, login, and JWT token generation._

### Setup & Run

1. Navigate to the directory: `cd auth`
    
2. Create virtual environment & install dependencies:
    
    Bash
    
    ```
    python -m venv venv
    source venv/bin/activate  # Windows: .\venv\Scripts\activate
    pip install -r requirements.txt
    ```
    
3. Configure `.env` file (See `core/config.py` for reference):
    
    Code snippet
    
    ```
    MONGO_URI=...
    JWT_SECRET_KEY=...
    ```
    
4. **Start Server:**
    
    Bash
    
    ```
    uvicorn main:app --reload --port 8001
    ```
    

> **Note:** The Auth service runs on **Port 8001** (Example).

---

## 2. Before Service (AI Travel Consultant)

_Handles intelligent destination recommendations using Hybrid Search (Keywords + Semantic) and Generative AI (RAG)._

This service acts as a smart travel consultant. It allows users to filter destinations by hard constraints (budget_range, location_province, available_time, seasons, companion) or discover new places by describing their "vibe" or preferences (e.g., "a quiet place for healing"). The system uses **Google Gemini** to generate personalized justifications for each recommendation.

### 🛠 Prerequisites (Specific to Before Module)

- **Python 3.10+**
- **MongoDB Atlas Account** (Must have a Vector Search Index configured).
- **Google Gemini API Key** (Get it from Google AI Studio).
- **OpenWeatherMap API Key** (For real-time weather info).

### 📥 Installation & Setup

**1. Navigate to the folder:**

```bash
cd backend/Before
```
**2. Create and activate a virtual environment:**
```bash
# Recommended Python 3.10
python -m venv venv

# Windows:
.\venv\Scripts\activate

# Mac/Linux:
source venv/bin/activate
```
**3. Install dependencies:**
```bash
pip install -r requirements.txt
```
**4. Environment Configuration:**

Create a .env file in the before directory. Configure the following keys based on core/config.py:
```
# Database
MONGO_DB_URL=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
MONGO_DB_NAME=SmartTourismDB
DESTINATIONS_COLLECTION=Destinations

# LLM (Google Gemini)
GEMINI_API_KEY=your_google_gemini_api_key
GEMINI_MODEL_NAME=gemini-1.5-flash

# Weather
OPENWEATHER_API_KEY=your_openweather_api_key

# Auth & Security
SECRET_KEY=your_super_secret_key (Must match Auth Service key)
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# Data Paths
VECTORIZER_PATH=modules/vectorizer.pkl
EXCEL_FILE_PATH=data/destinations.xlsx
```
**5. Data Ingestion (First Run Only):**

Before starting the API, you must load the travel data from Excel into MongoDB and train the Hybrid Vectorizer.

```bash
python ingest_data.py
```
_Note: Wait for the message: `✅ Ingestion complete. Data is safe` . This process generates the `vectorizer.pkl` file and populates your MongoDB collection._
### 🗄️ MongoDB Atlas Search Index Configuration
_To enable Hybrid Search, you must create a Vector Search Index on your Destinations collection in MongoDB Atlas._

1. Go to your `MongoDB Atlas Dashboard`.

2. Navigate to `Atlas Search -> Create Search Index`.

3. Select `JSON Editor`.

4. Choose the Database and Collection (`Destinations`).

5. Name the index: `vector_index` (Important: Must match the code).

6. Paste the following configuration into the JSON editor:

```JSON

{
  "fields": [
    {
      "type": "vector",
      "path": "v_hybrid",
      "numDimensions": 7830,
      "similarity": "cosine"
    },
    {
      "type": "filter",
      "path": "budget_range"
    },
    {
      "type": "filter",
      "path": "available_time"
    },
    {
      "type": "filter",
      "path": "companion_tag"
    },
    {
      "type": "filter",
      "path": "season_tag"
    },
    {
      "type": "filter",
      "path": "location_province"
    }
  ]
}
```
_Note: The numDimensions: 7830 corresponds to the combined dimension of `TF-IDF + SBERT` generated by the `HybridVectorizer`. If you change your dataset significantly, this dimension might change, and you will need to update the index accordingly._
### 🚀 How to Run the Before Service
**1. Start the Server:**

```Bash

python main.py
```
Note: The service runs on Port 8001.

**2. Access Swagger UI:**

Open your browser and navigate to: http://127.0.0.1:8001/docs

### 📖 Step-by-Step API Usage Guide
#### A. Explore & Filter (`GET /destinations`)
_Find destinations using specific criteria without AI._

1. Find **`GET /destinations`**.

2. Click **Try it out**.

3. Set parameters:

+ `budget_range`: enter **thấp**, **trung bình** or **cao**.

+ `location_province`: enter **Thành phố Hồ Chí Minh** (optional).

+ `sort_by`: select **RATING_DESC**.

4. Click **Execute**.

5. **Result**: A paginated list of destinations matching your filters.

#### B. Hybrid Search (`POST /search`)
_Search using keywords combined with filters (e.g., "sea travel" + "low budget")._

1. Find **`POST /search`**.

2. Click **Try it out**.

3. Request Body:
```
JSON

{
  "query": "Du lịch biển ngắm hoàng hôn",
  "hard_constraints": {
    "budget_range": ["thấp", "trung bình"]
    "companion_tag": ["cặp đôi", "gia đình"]
  }
}
```
4. Click **Execute**.
5. **Result**: Destinations that match both the keyword "biển" semantically and the budget constraint.

#### C. AI Recommendation (POST /recommendations)
_Get personalized suggestions with AI-generated reasons (RAG)._

1. Find **`POST /recommendations`**.

2. Click **Try it out**.

3. Request Body:

```
JSON

{
  "vibe_prompt": "Tôi muốn tìm một nơi thật yên tĩnh, vắng vẻ để chữa lành tâm hồn vào cuối tuần."
}
```
4. Click **Execute**.

5. **Result**: Top 3 recommended places. Each item includes a `justification_summary `field where AI explains why this place fits your "healing" vibe.

#### D. Manage Favorites (POST /favorites/{id})
_Save a destination to your personal list (Requires Auth)._

1. **Authorize**: Click the lock icon 🔒 (top right) and enter a valid JWT Token (from Auth Service).

2. Find **`POST /favorites/{landmark_id}`**.

3. Enter a valid ID (copy from previous search results).

4. Click **Execute**.

5. **Result**: Message `Đã thêm vào mục yêu thích`.

6. Verify: Use **`GET /favorites/`** to see your saved list.

## 3. During Service (Sightseeing Recognition)

_Handles visual search, AI detection, and detection history._

This project provides a backend API for a sightseeing recognition system using FastAPI, MongoDB, DINOv2, and Cloudinary. It allows users to search for landmarks via images, manage search history, and synchronize temporary guest history with registered user accounts.

### Prerequisites (Specific to During Module)

- **Python 3.10+** (Developed on 3.10.19)
    
- **MongoDB Atlas Account** (for vector search and data storage)
    
- **Cloudinary Account** (for image hosting)
    

### Installation

**1. Navigate to the folder:**

Bash

```
cd during
```

**2. Create and activate a virtual environment:**

Bash

```
# It is recommended to use Python 3.10
python3.10 -m venv venv

# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

**3. Install dependencies:**

Bash

```
pip install -r requirements.txt
```

 **4. Environment Configuration:**

Create a `.env` file in the root directory. You will need to configure the following variables (based on `core/config.py`):


```
# Database
MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority
DB_NAME=your_DB_name
DURING_COLLECTION=your_embeded_image_collection_name
BEFORE_COLLECTION=your_metadata_collection_name
HISTORY_COLLECTION=your_detection_history_collection_name
TEMP_HISTORY_COLLECTION=your_temp_detection_history_collection_name

# Cloudinary
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret

# Auth
JWT_SECRET_KEY=your_super_secret_key (Must match Auth Service key)
JWT_ALGORITHM=HS256

# Model
MODEL_NAME=facebook/dinov2-base
MODEL_PATH=path/to/your/finetuned_model.pth  # Optional if loading base model
DEVICE=cpu  # or cuda
```

### How to Run the During Service

The project uses Uvicorn as the ASGI server and includes an automatic model loading process on startup.
#### Prerequisites

Ensure you are in the **root directory** of the project (the folder containing `main.py`).
#### 1.  **Start the Server:**

Run the following command in your terminal:

```bash
    uvicorn main:app --reload
```

*Note: Wait for the log message:\

`✅ Fine-tuned DINOv2 ready!`\

`INFO:     Application startup complete.`
#### 2.  **Access Swagger UI:**

Open your web browser and navigate to:

```
    http://127.0.0.1:8000/docs
```

You will see the interactive API documentation provided by Swagger UI.
#### 3. **Step-by-Step API Usage Guide**
#### A. Authentication (Required for History/Sync/Delete)

Most features beyond basic search require you to be "logged in". In Swagger, we simulate this using a JWT Token.

1.  Click the **Authorize** button (top right of the page).

2.  In the **Value** box, enter your valid JWT Token (e.g., `eyJhbGciOiJIUz...`).

      * *Note: This token must be generated using the same `JWT_SECRET_KEY` configured in your `.env` file.*

3.  Click **Authorize** and then **Close**.

4.  The padlock icon next to endpoints will now appear "locked", meaning your requests will include the user credentials.

#### B. Visual Search (Guest vs. User)

Find the **`POST /visual-search`** endpoint.

1.  Click **Try it out**.

2.  **Upload Image:** Click the `Choose File` button in the `file` field and select an image.

3.  **Guest Mode (Simulation):**

      * Leave the `X-Temp-ID` field empty for the first request.

      * Click **Execute**.
    
      * **Response:** Look at the JSON response. Copy the `temp_id` (e.g., `550e8400-e29b...`) provided in the response body.

      * **Subsequent Requests:** Paste that UUID into the `X-Temp-ID` header field to simulate a guest continuing their session.

4.  **User Mode:**

      * If you successfully completed Step A (Authentication), the API will ignore the `X-Temp-ID` and save the result directly to your User History.
     
#### C. Synchronize History (`POST /history/sync`)

  * **Context:** This is a **hidden background function**. In the real application, the Frontend automatically calls this endpoint immediately after a user logs in to merge their "Guest History" into their "User Account".

  * **How to Test in Swagger:**

    1.  Ensure you have a `temp_id` from a previous Guest Search (see Step B).

    2.  Ensure you are Authorized (see Step A).

    3.  Find the **`POST /history/sync`** endpoint and click **Try it out**.

    4.  In the Request Body, paste the JSON containing your temp ID:

        ```json

        {

          "temp_id": "your-copied-uuid-here"

        }

        ```

    5.  Click **Execute**.

    6.  **Result:** The system will move all items from the Temporary collection to your Main User History and delete the temporary record.
  
#### D. View History Summary (`GET /history/summary`)

To verify your data, use the summary endpoint to get a list of your past activities.

1.  Ensure you are Authorized.

2.  Find the **`GET /history/summary`** endpoint.

3.  Click **Try it out** -\> **Execute**.

4.  **Result:** You will see a list of all landmarks you have searched for (including the ones you just synced).

5.  **Tip:** Copy a `landmark_id` (e.g., `lm_eiffel_tower`) from this list to use in the next step.

#### E. View History Details (`GET /history/detail/{landmark_id}`)

This endpoint provides full metadata about a specific detection, including the matched reference image and detailed description from the database.

1.  Ensure you are Authorized.

2.  Find the **`GET /history/detail/{landmark_id}`** endpoint and click **Try it out**.

3.  **Input:** Paste the `landmark_id` you copied from the Summary list into the field.

4.  Click **Execute**.

5.  **Result:** You will receive a detailed JSON object containing the landmark's full information (description, location, tags) and the link to the reference image used for matching.

#### F. Delete History (`DELETE /history/delete`)

This endpoint allows you to remove specific items. It performs a "Dual Delete": removing the record from **MongoDB** and destroying the actual image on **Cloudinary**.

1.  Ensure you are Authorized.

2.  Find the **`DELETE /history/delete`** endpoint and click **Try it out**.

3.  In the Request Body, you must provide a JSON object containing the list of **User Image URLs** you want to delete (you can get these URLs from the Summary endpoint).

      * **Format:**

        ```json

        {

          "image_urls": [

            "https://res.cloudinary.com/your-cloud/image/upload/v1234/sample1.jpg",

            "https://res.cloudinary.com/your-cloud/image/upload/v1234/sample2.jpg"

          ]

        }

        ```

4.  Click **Execute**.

5.  **Result:** The API will return the count of deleted database records and the count of images removed from the cloud.
    
---
## 4. After Service (Feedback & Review)

_Handles post-trip reviews and ratings._

### Setup & Run

1. Navigate to the directory: `cd after`
    
2. Activate virtual environment & install dependencies.
    
3. Configure `.env` file.
    
4. **Start Server:**
    
    Bash
    
    ```
    uvicorn main:app --reload --port 8003
    ```
    

> **Note:** The After service runs on **Port 8003** (Example).

---

## 5. Frontend Application

_The user interface built with React/Vue/Mobile._

### Setup & Run

1. Navigate to the directory: `cd frontend`
    
2. Install dependencies:
    
    Bash
    
    ```
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
