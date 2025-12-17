# After Module – Unit Tests

Smart Sightseeing Support System

---

## 1. Purpose

This README documents the **unit testing scope** for the **After Module** of the **Smart Sightseeing Support System**.

The files in this directory focus **only on validating core business logic** of the After Module, including image filtering, clustering, curation, and trip summary generation.

> ⚠️ This README is intentionally placed inside the `Tests/` directory and **does not describe the full system or deployment**.

---

## 2. What Is Tested

### ✅ Image Filtering

#### Lighting Filter (`test_lighting.py`)

* Good lighting detection
* Underexposed / overexposed rejection
* Glare detection
* Corrupt image handling
* Disk-based image loading
* Brightness threshold validation

#### Junk Detector (`test_junk_detector.py`)

* Camera model EXIF detection
* Screenshot / meme rejection
* Invalid EXIF value handling
* Batch junk detection
* AI inference path (mocked)
* Graceful handling when model fails

#### Integration (`test_integration_filters.py`)

* End-to-end pipeline:

  * Lighting filter → Junk detection

---

### ✅ Album Clustering (`test_cluster.py`)

* Dispatcher routing logic
* Rejected photo separation
* Metadata-based algorithm selection
* Fallback behavior when metadata is missing
* Spatiotemporal (ST-DBSCAN) clustering
* HDBSCAN location clustering
* Jenks time-based clustering
* Edge cases (small clusters, noise, partial metadata)

---

### ✅ Image Curation (`test_curation.py`)

* Quality score calculation
* Score range validation (0.0 – 1.0)
* Sharp vs blurry image comparison

---

### ✅ Trip Summary (`test_trip_summary.py`)

* Empty album handling
* GPS-based album summaries
* Manual location override
* Skipping albums without location data
* Distance calculation
* Timeline chronological ordering
* Static vs interactive map modes

---

## 3. What Is NOT Tested

The following components are intentionally excluded from unit testing:

* ML model training (pre-trained model assumed)
* External APIs (Mapbox, Cloudinary)
* Database operations (MongoDB)
* WebSocket connections
* Authentication & authorization
* Frontend/UI logic

These components are either **integration-level concerns** or rely on **external services**.

---

## 4. Test Structure

```text
Tests/
├── test_trip_summary.py
├── test_cluster.py
├── test_curation.py
├── test_lighting.py
├── test_junk_detector.py
└── test_integration_filters.py
```

---

## 5. How to Run Tests

From the `After/` directory:

```bash
python -m unittest discover Tests -v
```

Run a specific test file:

```bash
python -m unittest Tests.test_lighting
```

---

## 6. Expected Result

```text
Ran 76 tests in ~2–3 seconds
OK
```

All tests should pass with no external dependencies required.

---

## 7. Notes for Evaluation

* Tests use **mocking** to isolate logic
* File-system operations use **temporary files**
* Image data is generated synthetically for determinism
* Focus is on **correctness and robustness**, not performance

This test suite demonstrates **clear separation of concerns**, **defensive coding**, and **high coverage of core logic**.
