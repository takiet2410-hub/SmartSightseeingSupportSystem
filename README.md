# Smart Tourism AI API

This project provides a backend API for a sightseeing recognition system using FastAPI, MongoDB, DINOv2, and Cloudinary. It allows users to search for landmarks via images, manage search history, and synchronize temporary guest history with registered user accounts.

## Prerequisites

  * **Python 3.10+** (Developed on 3.10.19)
  * **MongoDB Atlas Account** (for vector search and data storage)
  * **Cloudinary Account** (for image hosting)

## Installation

### 1.  **Clone the repository:**

```bash
    git clone <your-repo-url>
    cd <your-repo-folder>
 ```

### 2.  **Create and activate a virtual environment (recommended):**

```bash
    # It is recommended to use Python 3.10
    python3.10 -m venv venv

    # Windows:
    .\venv\Scripts\activate
    # Mac/Linux:
    source venv/bin/activate
```

### 3.  **Install dependencies:**

```bash
    pip install -r requirements.txt
```

### 4.  **Environment Configuration**
Create a `.env` file in the root directory. You will need to configure the following variables (based on `core/config.py`):

```env
    # Database
    MONGO_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/?retryWrites=true&w=majority (your MongoDB URI)
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
    JWT_SECRET_KEY=your_super_secret_key
    JWT_ALGORITHM=HS256

    # Model
    MODEL_NAME=facebook/dinov2-base
    MODEL_PATH=path/to/your/finetuned_model.pth  # Optional if loading base model
    DEVICE=cpu  # or cuda
```

## How to Run the Project

The project uses Uvicorn as the ASGI server and includes an automatic model loading process on startup.
### Prerequisites

Ensure you are in the **root directory** of the project (the folder containing `main.py`).

### 1.  **Start the Server:**
Run the following command in your terminal:

```bash
    uvicorn main:app --reload
```

*Note: Wait for the log message:\
`✅ Fine-tuned DINOv2 ready!`\
`INFO:     Application startup complete.`

### 2.  **Access Swagger UI:**
Open your web browser and navigate to:

```
    http://127.0.0.1:8000/docs
```

You will see the interactive API documentation provided by Swagger UI.

### 3. **Step-by-Step API Usage Guide**

#### A. Authentication (Required for History/Sync/Delete)

Most features beyond basic search require you to be "logged in". In Swagger, we simulate this using a JWT Token.

1.  Click the **Authorize** button (top right of the page).
2.  In the **Value** box, enter your valid JWT Token (e.g., `eyJhbGciOiJIUz...`).
      * *Note: This token must be generated using the same `JWT_SECRET_KEY` configured in your `.env` file.*
3.  Click **Authorize** and then **Close**.
4.  The padlock icon next to endpoints will now appear "locked", meaning your requests will include the user credentials.

#### B. Visual Search (Guest vs. User)

Find the **`POST /visual-search`** endpoint.

1.  Click **Try it out**.
2.  **Upload Image:** Click the `Choose File` button in the `file` field and select an image.
3.  **Guest Mode (Simulation):**
      * Leave the `X-Temp-ID` field empty for the first request.
      * Click **Execute**.
      * **Response:** Look at the JSON response. Copy the `temp_id` (e.g., `550e8400-e29b...`) provided in the response body.
      * **Subsequent Requests:** Paste that UUID into the `X-Temp-ID` header field to simulate a guest continuing their session.
4.  **User Mode:**
      * If you successfully completed Step A (Authentication), the API will ignore the `X-Temp-ID` and save the result directly to your User History.

#### C. Synchronize History (`POST /history/sync`)

  * **Context:** This is a **hidden background function**. In the real application, the Frontend automatically calls this endpoint immediately after a user logs in to merge their "Guest History" into their "User Account".
  * **How to Test in Swagger:**
    1.  Ensure you have a `temp_id` from a previous Guest Search (see Step B).
    2.  Ensure you are Authorized (see Step A).
    3.  Find the **`POST /history/sync`** endpoint and click **Try it out**.
    4.  In the Request Body, paste the JSON containing your temp ID:
        ```json
        {
          "temp_id": "your-copied-uuid-here"
        }
        ```
    5.  Click **Execute**.
    6.  **Result:** The system will move all items from the Temporary collection to your Main User History and delete the temporary record.

#### D. View History Summary (`GET /history/summary`)

To verify your data, use the summary endpoint to get a list of your past activities.

1.  Ensure you are Authorized.
2.  Find the **`GET /history/summary`** endpoint.
3.  Click **Try it out** -\> **Execute**.
4.  **Result:** You will see a list of all landmarks you have searched for (including the ones you just synced).
5.  **Tip:** Copy a `landmark_id` (e.g., `lm_eiffel_tower`) from this list to use in the next step.

#### E. View History Details (`GET /history/detail/{landmark_id}`)

This endpoint provides full metadata about a specific detection, including the matched reference image and detailed description from the database.

1.  Ensure you are Authorized.
2.  Find the **`GET /history/detail/{landmark_id}`** endpoint and click **Try it out**.
3.  **Input:** Paste the `landmark_id` you copied from the Summary list into the field.
4.  Click **Execute**.
5.  **Result:** You will receive a detailed JSON object containing the landmark's full information (description, location, tags) and the link to the reference image used for matching.

#### F. Delete History (`DELETE /history/delete`)

This endpoint allows you to remove specific items. It performs a "Dual Delete": removing the record from **MongoDB** and destroying the actual image on **Cloudinary**.

1.  Ensure you are Authorized.
2.  Find the **`DELETE /history/delete`** endpoint and click **Try it out**.
3.  In the Request Body, you must provide a JSON object containing the list of **User Image URLs** you want to delete (you can get these URLs from the Summary endpoint).
      * **Format:**
        ```json
        {
          "image_urls": [
            "https://res.cloudinary.com/your-cloud/image/upload/v1234/sample1.jpg",
            "https://res.cloudinary.com/your-cloud/image/upload/v1234/sample2.jpg"
          ]
        }
        ```
4.  Click **Execute**.
5.  **Result:** The API will return the count of deleted database records and the count of images removed from the cloud.
