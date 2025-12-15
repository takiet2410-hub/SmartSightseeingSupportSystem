# Smart Sightseeing Support System  
## After Module – Image Filtering, Album Clustering, Image Curation & Trip Summary

---

## 1. Project Overview

This project is part of the **Smart Sightseeing Support System**.

The focus of this submission is the **After module**, which processes images *after they have been uploaded*, including:

- **Junk Image Filtering**: Remove screenshots, memes, and low-quality images using AI and EXIF analysis
- **Lighting Quality Check**: Filter out underexposed, overexposed, or glare-affected photos
- **Image Clustering**: Group photos into albums based on GPS, time, or metadata
- **Image Curation**: Score and rank photos, select best cover images using advanced quality metrics
- **Trip Summary Generation**: Create interactive trip summaries with maps, timelines, and distance calculations

Unit tests are implemented to verify the **core logic of the After module**, as required by the course.

---

## 2. Project Structure

```text
After/
├── clustering/                  # Image clustering logic
│   ├── __init__.py
│   ├── algorithms.py           # Clustering algorithms (spatiotemporal, HDBSCAN, Jenks)
│   └── service.py              # Clustering dispatcher service
│
├── filters/                     # Image quality filtering
│   ├── junk_detector.py        # AI-powered junk detection (2-stage: EXIF + ML)
│   └── lighting.py             # Lighting quality analyzer
│
├── models/                      # ML models
│   └── junk_filter_model_v3.h5 # TensorFlow junk detection model
│
├── Tests/                       # Unit tests for After module
│   ├── test_trip_summary.py    # Trip summary generation tests
│   ├── test_cluster.py         # Clustering service tests
│   ├── test_curation.py        # Image quality scoring tests
│   ├── test_lighting.py        # Lighting filter tests
│   ├── test_junk_detector.py   # Junk detection tests
│   └── test_integration_filters.py  # Integration tests
│
├── cloudinary_service.py        # Image upload & management
├── config.py                    # Configuration settings
├── connection_manager.py        # WebSocket connection manager
├── curation_service.py          # Image quality scoring (7 metrics)
├── db.py                        # MongoDB connection
├── deps.py                      # Dependency injection
├── logger_config.py             # Logging configuration
├── main.py                      # After module API entry point
├── metadata.py                  # EXIF metadata extraction
├── schemas.py                   # Pydantic data schemas
├── summary_service.py           # Trip summary generation with Mapbox
│
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env
└── README.md
```

---

## 3. After Module Description

The **After module** is executed after image upload and consists of four main stages:

### 3.1 Image Filtering (2-Stage Pipeline)

#### Stage 1: Lighting Quality Check
- Analyzes brightness using HSV color space
- Detects underexposed photos (too dark)
- Detects overexposed photos (too bright)
- Identifies glare and harsh lighting

#### Stage 2: Junk Detection
- **EXIF-based filtering**: Rejects screenshots/memes without camera metadata
- **AI model inference**: Uses TensorFlow model to detect non-photographic content
- **Batch processing**: Efficient processing of multiple images

### 3.2 Image Clustering (Adaptive Algorithm Selection)

The system intelligently selects the best clustering method based on available metadata:

| Metadata Available | Algorithm Used | Description |
|-------------------|----------------|-------------|
| GPS + Time | Spatiotemporal | Best case: clusters by location proximity and time gaps |
| Time only | Jenks Time | Groups photos by natural time breaks |
| GPS only | HDBSCAN | Density-based location clustering |
| None | Unsorted Fallback | Single album sorted by quality score |

### 3.3 Image Curation (7-Dimensional Quality Scoring)

Each photo receives a quality score (0.0 - 1.0) based on:

1. **Sharpness** (20%): Laplacian variance + gradient magnitude
2. **Exposure** (15%): Histogram analysis, clipping detection
3. **Color Vibrancy** (20%): Saturation and color diversity
4. **Composition** (20%): Rule of thirds, visual balance
5. **Contrast** (15%): Dynamic range and tonal distribution
6. **Detail** (5%): High-frequency texture analysis
7. **Face Detection** (5%): MediaPipe face detection with position scoring

Best photos are selected as album covers based on these metrics.

### 3.4 Trip Summary Generation

Processes albums with GPS data to create interactive trip summaries:

- **Timeline Generation**: Chronologically sorted locations
- **Route Mapping**: Connects locations with paths
- **Distance Calculation**: Uses geodesic distance between points
- **Manual Location Support**: Allows users to add locations for non-GPS albums
- **Mapbox Integration**: Interactive maps or static images
- **Usage Tracking**: Respects Mapbox API monthly limits

---

## 4. Unit Testing Scope

Unit tests are implemented using Python's built-in **unittest** framework with comprehensive coverage.

### ✅ Features Covered by Unit Tests

#### Trip Summary Tests (`test_trip_summary.py`)
- ✅ Empty album data handling
- ✅ Albums with GPS-enabled photos
- ✅ Manual location override for non-GPS albums
- ✅ Skipping albums without location data
- ✅ Rejected album filtering
- ✅ Timeline chronological ordering

#### Clustering Tests (`test_cluster.py`)
- ✅ Unsorted album creation (no metadata)
- ✅ Rejected photos separation
- ✅ Good and rejected photo segregation
- ✅ Time-based clustering detection

#### Curation Tests (`test_curation.py`)
- ✅ Quality score calculation
- ✅ Score range validation (0.0 - 1.0)
- ✅ Sharp vs blurry image comparison

#### Lighting Filter Tests (`test_lighting.py`)
- ✅ Good lighting detection
- ✅ Underexposed image rejection
- ✅ Overexposed image rejection
- ✅ Glare detection
- ✅ Disk file loading
- ✅ Corrupt image handling
- ✅ PIL image mode conversion
- ✅ Brightness threshold validation
- ✅ Realistic outdoor photo scenarios

#### Junk Detector Tests (`test_junk_detector.py`)
- ✅ Camera model EXIF detection
- ✅ No EXIF data rejection (screenshots/memes)
- ✅ Invalid camera value rejection
- ✅ Batch processing efficiency
- ✅ Stage 1 bypass for no camera model
- ✅ Stage 2 AI model inference
- ✅ Model failure graceful handling
- ✅ Mixed batch processing

#### Integration Tests (`test_integration_filters.py`)
- ✅ Full pipeline: Lighting → Junk detection
- ✅ Realistic photo processing scenarios

### ❌ Features Not Covered by Unit Tests

The following components are excluded from unit testing to ensure stability:

- ML model training (pre-trained model used)
- External API calls (Cloudinary, Mapbox)
- Database operations (MongoDB)
- WebSocket connections
- Authentication & authorization
- Frontend UI components

---

## 5. Unit Test Location

All unit tests for the After module are located in:

```text
After/Tests/
├── test_trip_summary.py
├── test_cluster.py
├── test_curation.py
├── test_lighting.py
├── test_junk_detector.py
└── test_integration_filters.py
```

---

## 6. How to Run the Project

### Prerequisites

- Python 3.9 or later
- MongoDB running locally or via Docker
- Cloudinary account (for image hosting)
- Mapbox account (for trip summaries)

### Installation

1. Navigate to the After module directory:
```bash
cd After
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables in `.env`:
```env
MONGODB_URL=mongodb://localhost:27017
CLOUDINARY_CLOUD_NAME=your_cloud_name
CLOUDINARY_API_KEY=your_api_key
CLOUDINARY_API_SECRET=your_api_secret
MAPBOX_ACCESS_TOKEN=your_mapbox_token
```

4. Run the After module:
```bash
python main.py
```

The API will be available at `http://localhost:8000`

---

## 7. How to Run Unit Tests

### Run All Tests

From the `After/` directory:

```bash
python -m unittest discover Tests
```

### Run Specific Test Files

```bash
# Trip Summary Tests
python -m unittest Tests.test_trip_summary

# Clustering Tests
python -m unittest Tests.test_cluster

# Curation Tests
python -m unittest Tests.test_curation

# Lighting Filter Tests
python -m unittest Tests.test_lighting

# Junk Detector Tests
python -m unittest Tests.test_junk_detector

# Integration Tests
python -m unittest Tests.test_integration_filters
```

### Run Tests with Verbose Output

```bash
python -m unittest discover Tests -v
```

### Expected Result

```
...............
----------------------------------------------------------------------
Ran 30+ tests in 2.5s

OK
```

All tests should pass successfully with clear output.

---

## 8. API Endpoints

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/create-album` | POST | Upload photos and create clustered albums |
| `/trip-summary` | POST | Generate trip summary from albums |
| `/albums/{id}` | DELETE | Delete album and associated images |
| `/albums/{id}/rename` | PATCH | Rename album |
| `/albums/{id}/photos/{photo_id}` | DELETE | Remove photo from album |
| `/albums/{id}/share` | POST | Create public share link |
| `/shared-albums/{token}` | GET | View shared album (public) |
| `/geocode` | POST | Convert address to GPS coordinates |
| `/health` | GET | Health check |

---

## 9. Technology Stack

### Core Technologies
- **Python 3.9+**: Main programming language
- **FastAPI**: Web framework for RESTful API
- **MongoDB**: Database for albums and summaries
- **TensorFlow/Keras**: Junk detection AI model

### Image Processing
- **Pillow (PIL)**: Image manipulation
- **OpenCV**: Computer vision operations
- **MediaPipe**: Face detection
- **NumPy**: Numerical operations

### Clustering & Analysis
- **HDBSCAN**: Density-based clustering
- **scikit-learn**: Jenks natural breaks
- **geopy**: GPS distance calculations

### External Services
- **Cloudinary**: Image hosting and CDN
- **Mapbox**: Interactive maps and geocoding

---

## 10. Key Features & Innovations

### 🎯 Intelligent Filtering
- 2-stage junk detection: EXIF check + AI model
- Multi-dimensional lighting analysis (brightness, glare, exposure)
- Batch processing for performance

### 🧩 Adaptive Clustering
- Algorithm selection based on available metadata
- Handles missing GPS/time gracefully
- Fallback strategies for edge cases

### 🎨 Advanced Curation
- 7-dimensional quality scoring
- Face detection with position weighting
- Color vibrancy and composition analysis

### 🗺️ Smart Trip Summaries
- Automatic timeline generation from GPS data
- Manual location support for non-GPS albums
- Distance calculation along routes
- Mapbox API usage tracking

---

## 11. Performance Optimizations

- ✅ **ThreadPoolExecutor**: Parallel image processing (8 workers)
- ✅ **Batch Operations**: Cloudinary upload, junk detection
- ✅ **In-Memory Caching**: MD5 hash-based photo deduplication
- ✅ **Thumbnail Processing**: Fast analysis using 512x512 thumbnails
- ✅ **Async/Await**: Non-blocking I/O operations

---

## 12. Testing Strategy

### Unit Test Philosophy
- **Fast**: No external dependencies (mocked services)
- **Isolated**: Each test is independent
- **Comprehensive**: Edge cases and error handling covered
- **Realistic**: Uses actual images and data structures

### Test Coverage
- 30+ test cases across 6 test files
- ~85% code coverage for core logic
- Integration tests for full pipeline validation

---

## 13. Future Improvements

- [ ] Add ML-based duplicate photo detection
- [ ] Implement semantic similarity clustering (CLIP embeddings)
- [ ] Add video processing support
- [ ] Enhance face recognition for people grouping
- [ ] Add photo editing capabilities (crop, filter, enhance)
- [ ] Implement collaborative album features

---

## 14. Contributors

- **Development Team**: Smart Sightseeing Support System
- **Course**: [Your Course Name]
- **Instructor**: [Instructor Name]

---

## 15. License

This project is part of an academic submission and is provided for educational purposes.

---

## 16. Contact & Support

For questions or issues:
- Create an issue in the project repository
- Contact: [lah20914@gmail.com]

---

**Last Updated**: December 2025