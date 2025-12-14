# Smart Sightseeing Support System  
## After Module – Image Filtering, Album Clustering, Image Curation & Trip Summary

---

## 1. Project Overview

This project is part of the **Smart Sightseeing Support System**.

The focus of this submission is the **After module**, which processes images *after they have been uploaded*, including:

- Filtering out low-quality or irrelevant images (junk image filtering)
- Clustering images into albums
- Selecting the best image as the album cover
- Generating a Trip Summary for users

Unit tests are implemented to verify the **core logic of the After module**, as required by the course.

---

## 2. Project Structure

```text
backend/
├── After/
│   ├── __pycache__/
│   │
│   ├── clustering/                  # Image clustering logic
│   │   ├── __init__.py
│   │   ├── algorithms.py
│   │   └── service.py
│   │
│   ├── filters/                     # Image quality filtering
│   │   ├── junk_detector.py
│   │   └── lighting.py
│   │
│   ├── models/                      # ML models
│   │   └── junk_filter_model_v3.h5
│   │
│   ├── Tests/                       # Unit tests for After module
│   │   └── test_trip_summary.py
│   │
│   ├── cloudinary_service.py        # Image upload service
│   ├── config.py                    # Configuration settings
│   ├── connection_manager.py        # WebSocket connection manager
│   ├── curation_service.py          # Image curation & cover selection
│   ├── db.py                        # Database connection
│   ├── deps.py                      # Dependency injection
│   ├── logger_config.py             # Logging configuration
│   ├── main.py                      # After module entry point
│   ├── metadata.py                  # Image metadata processing
│   ├── schemas.py                   # Data schemas
│   ├── summary_service.py           # Trip summary generation logic
│   │
│   ├── mapbox_usage.txt
│   ├── requirements.txt
│   ├── Dockerfile
│   ├── docker-compose.yml
│   ├── .dockerignore
│   ├── .env
│   └── .gitkeep
│
├── requirements.txt
├── docker-compose.yml
└── README.md

````

---

## 3. After Module Description

The **After module** is executed after image upload and is responsible for the following steps:

### 3.1 Image Filtering

* Remove junk or low-quality images
* Filter images based on lighting and quality criteria

### 3.2 Image Clustering

* Group remaining images into albums based on similarity
* Ensure each image belongs to exactly one album

### 3.3 Image Curation

* Select the best image from each album as the album cover
* The selection is based on image quality and filtering results

### 3.4 Trip Summary Generation

* Process albums containing GPS data
* Apply manual location for albums without GPS
* Generate a Trip Summary including:

  * Timeline
  * Route points
  * Total locations
  * Distance estimation

---

## 4. Unit Testing Scope

Unit tests are implemented using Python’s built-in **unittest** framework.

### Features Covered by Unit Tests

* Trip summary generation from clustered albums
* Handling albums without GPS using manual location
* Skipping invalid albums (no GPS and no manual location)
* Correct timeline ordering based on timestamp
* Validation of trip summary output structure

### Features Not Covered by Unit Tests

The following components are excluded from unit testing to ensure stability and determinism:

* Machine learning model inference
* Image feature extraction
* Database operations
* Mapbox API calls
* Authentication and UI

---

## 5. Unit Test Location

All unit tests for the After module are located at:

```text
backend/After/Tests/test_trip_summary.py
```

Each important feature of the After module has at least one test case to verify correct behavior.

---

## 6. How to Run the Project

### Ensure Python 3.9 or later is installed.

Make sure you are inside the `backend/After` directory.

(Optional) Install dependencies:

```bash
pip install -r requirements.txt
```

Run the After module:

```bash
python After/main.py
```

---

## 7. How to Run Unit Tests

### Run unit tests for the After module

Make sure you are inside the `backend/After` directory:


```bash
python -m unittest Tests/test_trip_summary.py
```

Or run all tests in the backend:

```bash
python -m unittest discover Tests
```

Expected result:

* All tests pass successfully
* Clear test output is displayed

---
