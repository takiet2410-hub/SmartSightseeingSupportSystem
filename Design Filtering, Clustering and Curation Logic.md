# Design Filtering

> **Problem Context:**
>
> A tourist has just finished their trip (the "After" phase). They open their photo library and see a chaotic mess of 500 photos.
>
> The problem isn't damaged photos (blurry/dark), but that the library is "cluttered" with a lot of **Junk Photos**: 3 exact duplicates, 15 near-identical burst shots, 5 screenshots, 2 receipts, and 1 photo accidentally taken of the ground.
>
> The fatigue of manually reviewing and deleting 500 photos is a major psychological barrier. It makes the user give up on creating an album, and the photos are "imported and forgotten." They need an automated assistant to "clean up" this mess, leaving only the **meaningful** photos as raw material for the next phase (Clustering).

-----

## 🎯 1) Identify Stakeholders

  * **Tourist (End User):** The person directly suffering from the "clutter." They want a clean library but are **afraid** the system will mistakenly delete a precious memory (False Positive) that "looks like" junk (e.g., deleting the one burst shot where they are smiling best).
  * **Clustering System:** The "victim" of dirty data. If filtering fails, the Clustering System will receive junk and create meaningless clusters (e.g., a cluster of 15 burst photos, a cluster of 5 screenshots), diluting the "story" results.
  * **Service Provider (Platform):** Wants to save on cloud storage costs. Filtering junk photos (especially duplicates) significantly reduces storage consumption.

-----

## 📈 2) Clarify Objectives

The overall objective is to automatically classify and suggest the removal of photos with no content value (junk), in order to maximize the library's relevance and minimize user effort.

### 01: Maximize Cleaning Efficiency

1.  **1.1 (Duplicate Detection):** Automatically identify and suggest deleting **100%** of exact duplicates (same hash).
2.  **1.2 (Junk Content Detection):** Automatically identify and suggest deleting **\> 95%** of obvious "junk" photos (e.g., `screenshot`, `receipt`, `document`).
3.  **1.3 (Burst Handling):** Automatically group burst shots (near-duplicates) and suggest keeping only the 1-2 "best" representative shots.

### 02: Maximize Trust & Accuracy

This is the most important objective, prioritized over 100% cleaning efficiency.

1.  **2.1 (False Positive Rate):** The rate at which the system flags a *meaningful* memory as "junk" must be **\< 0.1%**. (e.g., it must not delete a photo of a restaurant menu if the user intended to keep it).
2.  **2.2 (Quick Approval Rate):** **\> 80%** of users accept the system's "Delete All" suggestion without reviewing each photo individually (indicating high trust).

### 03: Optimize Downstream Quality

1.  **3.1 (Cluster Purity):** Enabling the filter must reduce the number of "junk clusters" (e.g., screenshot clusters) in Phase 4.3 (Clustering) by at least **80%**.

-----

## 📥 3) Define Inputs and Expected Outputs

### A. Inputs

1.  **User Inputs:**
      * A collection of unprocessed photos.
2.  **System Inputs:**
      * **Image File:** Raw pixel data.
      * **Image Metadata:**
          * `Timestamp` (crucial for detecting bursts).
          * `File Hash` (MD5/SHA256, for 100% duplicate detection).
      * **Classification Models:** (Pre-trained)
          * **Content Classification Model:** To assign labels (e.g., `screenshot`, `receipt`, `document`, `normal_photo`).
      * **Feature Models:**
          * **Feature Vectors (e.g., CLIP, ResNet):** To find "near-duplicate" images visually.
          * **Quality Scorer Function:** (Still necessary) Used to select the "best" photo (sharpest, best composition) from a burst series.

### B. Expected Outputs

1.  **Primary Output (For the System):**
      * A **Clean List:** Contains photos that passed the filter, ready for Phase 4.3 (Clustering).
2.  **Supporting Outputs (For the User):**
      * A **Deletion List:** Contains flagged photos.
      * **Reason Tag:** Crucial for building trust. (e.g., `reason: "Duplicate"`, `reason: "Screenshot"`, `reason: "Burst shot"`).
      * **Interactive UI:**
          * "We found 5 screenshots and 3 burst groups. Would you like to clean them up?"
          * **(Important)** An interface to "Choose the best shot" for burst groups, allowing the user to override the AI's choice.

-----

## 🛠️ 4) Solution & Tools (How?)

How and what tools to use to filter the 3 main types of junk photos?

### 1\. Tools

  * **Programming Language:** **Python**.
  * **Hashing Library (for 1.1):** `hashlib` (built into Python) to calculate `MD5` or `SHA256` hash of the image file.
  * **AI/CV Libraries (for 1.2 & 1.3):**
      * **TensorFlow/Keras** or **PyTorch:** To run AI models.
      * **OpenCV:** To calculate quality scores (sharpness) for burst photos.
      * **Pillow (PIL):** For basic image processing (open, resize) before feeding into models.

### 2\. Logic (How-to)

A processing pipeline will run in 3 steps:

#### Step 1: Filter Duplicates (Objective 1.1)

  * **Logic:** Use **Hashing**.
  * **How-to:**
    1.  Create an empty `set` called `seen_hashes`.
    2.  Iterate through each photo.
    3.  Calculate the `file_hash` (e.g., MD5) for the image file.
    4.  If `file_hash` is already in `seen_hashes`, mark this photo as `junk_reason: "Duplicate"`.
    5.  Otherwise, add `file_hash` to `seen_hashes`.
  * **Result:** Removes 100% of identical files.

#### Step 2: Filter Junk Content (Objective 1.2)

  * **Logic:** Use **Image Classification**.
  * **How-to:**
    1.  Take the photos *not* marked as duplicates.
    2.  Use an image classification model (e.g., **MobileNetV2**, fast and lightweight) that has been trained to recognize classes like `screenshot`, `receipt`, `document`, and `normal_photo`.
    3.  Run each photo through the model.
    4.  If the model predicts `screenshot` or `receipt` with \> 95% confidence, mark the photo as `junk_reason: "Screenshot"`.
  * **Result:** Removes obvious content-based junk.

#### Step 3: Handle Burst Shots (Objective 1.3)

  * **Logic:** Combine **Time-based Clustering** and **Quality Scoring**.
  * **How-to:**
    1.  Take the remaining photos (passed Steps 1 and 2).
    2.  **Sort** the entire list by `timestamp`.
    3.  Iterate through the sorted list, finding "Time Bursts" - e.g., groups of photos taken less than 2 seconds apart.
    4.  **For each Time Burst (Burst Group):**
          * (Optional, advanced): Calculate a **Perceptual Hash** (e.g., `pHash`) for photos in the group. If pHashes are too different, they aren't a burst (e.g., 1 selfie, 1 landscape).
          * **Score Quality:** Use **OpenCV** (`cv2.Laplacian(img).var()`) to calculate the `blur_score` (sharpness) for EVERY photo in the group.
          * **Select Best Shot:** Keep the photo with the highest `blur_score`.
          * Mark all other photos in the group as `junk_reason: "Burst shot"`.

-----

## 🚧 5) State Constraints

Barriers that make building this "junk" filter difficult.

### 1\. Semantic Ambiguity

  * **This is the BIGGEST constraint.** "Junk" is a subjective concept.
  * **Example 1:** A screenshot of a map is "junk" after the trip, *but* a screenshot of a funny text message is a "memory."
  * **Example 2:** A photo of a restaurant menu or a receipt can be "junk," *but* it can also be part of a travel "journal" the user wants to keep.
  * The system cannot understand the user's *intent* when they captured the photo.

### 2\. Technical & Algorithm Constraints

  * **"Best Photo" Selection:** When processing 10 burst shots, choosing the "best" one is very hard. "Best" could mean: sharpest (easy), no one is blinking (hard), everyone is smiling (very hard), best composition (extremely hard).
  * **Distinguishing Near-Duplicate vs. Different:** It's very difficult to set a threshold to distinguish "two burst shots" (near-identical) from "two photos of the same landmark from different angles" (different).

### 3\. Data Constraints

  * **Junk data is diverse:** "Junk" is a moving target. Today it's receipts, tomorrow it's memes, the next day it's screenshots from a new app. The content classification model must be continuously updated.

### 4\. User & Trust Constraints

  * **Fear of False Positives:** As stated, users would rather tolerate clutter than lose a memory. The system must **never** *automatically delete* without asking, which adds a layer of friction to the "automatic" process.

-----

-----

# Design Clustering

> **Problem Context:**
>
> After Phase 4.2 (Filtering) is complete, the user (Tourist) has a "Clean List" of, for example, 300 "good" photos.
>
> The current problem is that this list is still **flat**. It's just an endless scroll of 300 photos sorted by time. The user has no way to "skim" their trip in a meaningful way.
>
> They can't see "What did we do on Day 1?" or "Where are the photos from the museum?" The fatigue of "cleaning junk" (4.2) is now replaced by the fatigue of "searching" in a clean but overly long list.
>
> They need the system to automatically **group** these 300 photos into meaningful "chapters" or "scenes," based on the context they were taken (Time and Location).

-----

## 🎯 1) Identify Stakeholders

  * **Tourist (End User):** The direct beneficiary. They want to review their trip as a well-organized "story" (e.g., "Day 1: Visiting the Cathedral, Lunch in District 1"), not a long photo roll.
  * **Story Generation System (Phases 4.4/4.5):** This is an internal "customer." It *needs* structured data input. It can't select a "Cover Photo for Day 1" (4.5.1) if it doesn't know which photos "Day 1" contains (4.3.1). It can't name a "Visit to the Museum" if it doesn't know which photos belong to the "Museum Cluster" (4.3.2).
  * **Service APIs:** (e.g., Google Maps, Nominatim). These services are used in 4.3.3 to provide names for GPS clusters. They are concerned with the number of API calls (which may cost money).

-----

## 📈 2) Clarify Objectives

The overall objective is to transform a flat, filtered list of photos into a context-rich data structure, organized along two primary axes (Time and Location), to serve as the foundation for automatic album creation.

### 01: Organize by Time Axis (4.3.1)

This is the main navigation structure, like "Chapters" in a book.

1.  **1.1 (Absolute Partition):** 100% of photos in the `Clean List` must be assigned to a "Day X" group (e.g., "Day 1", "Day 2").
2.  **1.2 (Reasonable Day Threshold):** The day-break logic must be reasonable. (e.g., "Day 1" is determined by the *first* photo's date, not the 1st of the month).

### 02: Organize by Location Axis (4.3.2)

This is the semantic structure, like "Scenes" within a Chapter.

1.  **2.1 (Cluster Accuracy):** The generated GPS clusters must "feel" correct to a human. Photos taken at the same venue (e.g., within 100m) must belong to the same cluster.
2.  **2.2 (Coverage):** \> 90% of photos *with valid GPS data* must be assigned to a location cluster (not "noise" - cluster -1).
3.  **2.3 (Noise Handling):** The system must be robust to "noisy" GPS data points (e.g., photos taken on a bus, GPS drift). DBSCAN handles this well by assigning them the `-1` label.

### 03: Semantic Enrichment (4.3.3)

Make the location clusters human-readable.

1.  **3.1 (Name Usefulness):** \> 90% of location clusters (e.g., with \> 3 photos) must be assigned a *meaningful* name (e.g., "Notre Dame Cathedral" or "Dong Khoi Street Area") instead of "Cluster 0" or coordinates `(10.77, 106.69)`.
2.  **3.2 (Naming Speed):** The API call to name each cluster must be fast (e.g., \< 2 seconds) to not slow down the entire process.

-----

## 📥 3) Define Inputs and Expected Outputs

### A. Inputs

1.  **Primary Input:**
      * `Clean List`: A list of photo objects from Phase 4.2.
2.  **Required Data per Photo:**
      * `image_id`: (Unique identifier)
      * `timestamp`: (ISO 8601 string, required for 4.3.1)
      * `location`: (A tuple `(latitude, longitude)`, required for 4.3.2)
3.  **System Parameters:**
      * For 4.3.2 (DBSCAN): `eps` (clustering radius, e.g., 100 meters) and `min_samples` (minimum photos, e.g., 3 photos).
      * For 4.3.3: `API Key` (For the Reverse Geocoding service).

### B. Expected Outputs

1.  **Output 1 (for 4.3.1): Day Structure**
      * A data structure (e.g., dictionary/map) mapping the Day Name to a list of photos.
      * `DayClusters = { "Day 1": [imgA, imgB, ...], "Day 2": [imgC, ...] }`
2.  **Output 2 (for 4.3.2): Location Labels**
      * This is *not* a new structure, but an **update** to the `Clean List`.
      * Each photo object in the `Clean List` now has an additional property: `cluster_id`.
      * `CleanList = [ {id: imgA, ts: ..., loc: ..., cluster_id: 0}, {id: imgB, ts: ..., loc: ..., cluster_id: 0}, {id: imgC, ts: ..., loc: ..., cluster_id: -1} ]`
3.  **Output 3 (for 4.3.3): Cluster Name Map**
      * A data structure (e.g., dictionary/map) mapping `cluster_id` to a human-readable name.
      * `ClusterNames = { 0: "Notre Dame Cathedral Area", 1: "War Remnants Museum", ... }`

-----

## 🛠️ 4) Solution & Tools (How?)

How and what tools to use to cluster by Time and Location?

### 1\. Tools

  * **Programming Language:** **Python**.
  * **Library (for 4.3.1):** `datetime` and `collections.defaultdict` (built into Python).
  * **Library (for 4.3.2):**
      * **Scikit-learn (`sklearn`):** Specifically, `sklearn.cluster.DBSCAN`.
      * **NumPy:** To prepare the coordinate array for `sklearn`.
  * **Library (for 4.3.3):**
      * **Geopy:** A Python library to access Geocoding services.
      * **Service API:** **Nominatim (OpenStreetMap)** (free) or **Google Maps Geocoding API** (paid, more accurate).

### 2\. Logic (How-to)

#### Function 4.3.1: Cluster by Day

  * **Logic:** Grouping based on date delta.
  * **How-to:**
    1.  Iterate through `Clean List`, converting `timestamp` (string) into `datetime` objects.
    2.  **Sort** the `Clean List` by the `datetime` object.
    3.  Get the start date: `start_date = clean_list[0].datetime_obj.date()`.
    4.  Create a `defaultdict(list)`.
    5.  Iterate through the sorted list; for each photo:
          * Calculate `day_number = (photo.datetime_obj.date() - start_date).days + 1`.
          * Assign the photo to the dict: `day_clusters[f"Day {day_number}"].append(photo)`.
    6.  Return `day_clusters`.

#### Function 4.3.2: Cluster by GPS (DBSCAN)

  * **Logic:** Run DBSCAN on spherical coordinates (haversine).
  * **How-to:**
    1.  Filter the `Clean List` to get only photos with GPS data.
    2.  Create a NumPy array `coords` containing the `(lat, lon)` from these photos.
    3.  **Convert:** Use `np.radians(coords)` to convert all coordinates to **radians** (required for `haversine`).
    4.  **Convert Epsilon:** `eps_in_radians = eps_meters / 6371000` (where 6371000 is Earth's radius in meters).
    5.  Initialize DBSCAN: `db = DBSCAN(eps=eps_in_radians, min_samples=3, metric='haversine', algorithm='ball_tree')`.
    6.  Run clustering: `db.fit(radians_coords)`.
    7.  Get labels: `labels = db.labels_` (will be `-1` for noise, `0`, `1`, `2`... for clusters).
    8.  Iterate through the photo list and `labels`, assigning `photo['cluster_id'] = label` accordingly.

#### Function 4.3.3: Name Clusters

  * **Logic:** Use Reverse Geocoding on the cluster's centroid (center point).
  * **How-to:**
    1.  Create a `defaultdict(list)` to group photos by `cluster_id` (from 4.3.2, skipping `-1`).
    2.  Create an empty `dict` `cluster_name_map`.
    3.  Initialize API (e.g., `geolocator = Nominatim(user_agent="my-app")`).
    4.  Iterate through the grouped clusters: `for cluster_id, photos_in_cluster in grouped_clusters.items():`
          * Calculate the centroid: `mean_lat = mean([p.lat for p in photos_in_cluster])`, same for `mean_lon`.
          * Call API: `location = geolocator.reverse((mean_lat, mean_lon), language='en')`.
          * Get name (e.g., `location.raw.get('name')` or part of `location.address`).
          * Save name: `cluster_name_map[cluster_id] = clean_name`.
    5.  Return `cluster_name_map`.

-----

## 🚧 5) State Constraints

Barriers that make building this clustering module difficult.

### 1\. Data Constraints

  * **Missing or Poor GPS Data:** This is the **biggest** constraint.
      * **Indoors:** Photos taken in museums, restaurants, or hotels often have *no* GPS signal. These photos cannot be clustered by location.
      * **GPS Drift:** GPS signals in urban areas (between tall buildings) tend to "drift." 10 photos taken at the same intersection might be recorded at 10 different locations 50m apart. This will *break* DBSCAN.

### 2\. Algorithm Constraints

  * **DBSCAN Sensitivity (4.3.2):**
      * Choosing the `eps` (radius) parameter is critical and difficult. `eps = 100m` might be good for a city center, but too *small* for a sprawling resort (like a beach) and too *large* for a single street (e.g., incorrectly grouping 3 different shops into one).
  * **The "Midnight" Problem (4.3.1):**
      * The simple "cluster by day" logic can be wrong. A party that starts at 10 PM (Day 1) and ends at 2 AM (Day 2) is *one* event in the user's mind, but function 4.3.1 will split it into *two* days, breaking the "story" logic.

### 3\. Service & Cost Constraints

  * **API Cost (4.3.3):** Reverse Geocoding services (like Google Maps) charge per call. If a trip generates 50 location clusters, the system must make 50 calls, incurring a cost.
  * **API Usefulness (4.3.3):** The API might return a name that is "correct" but "useless."
      * **Example 1 (Too general):** Returning "Ben Nghe Ward, District 1" instead of "Notre Dame Cathedral."
      * **Example 2 (Too specific):** Returning "135 Nam Ky Khoi Nghia Street" instead of "Reunification Palace."

-----

-----

# Design Curation Logic

> **Problem Context:**
>
> After Phase 4.3 (Clustering) is complete, we have groups of photos (e.g., "Day 1", "Notre Dame Cathedral Area").
>
> The problem is that these clusters are still **"fat"**. The "Notre Dame Cathedral Area" cluster might contain 50 photos. This is an improvement over 300 photos (from 4.3), but still too many.
>
> When the user (Tourist) or the system wants to see a "summary" of this cluster, they suffer from **Choice Paralysis**. The system needs to create a "cover photo" for this "chapter" of the story, but it doesn't know which of the 50 photos to pick.
>
> They need an "editor" (Curation Logic) to automatically review all 50 photos and **curate** a single, **best (Best Shot)** photo to represent the entire cluster.

-----

## 🎯 1) Identify Stakeholders

  * **Tourist (End User):** The primary beneficiary. They want to see their *best* photo used as the cover. A well-chosen "Best Shot" (e.g., a sharp selfie, a clear landscape) makes them feel good. A poorly chosen one (e.g., blurry, a mistake) devalues the whole album.
  * **Album Generation System:** The direct internal "customer." It *needs* a `cover_image` to display in the album summary UI. It cannot proceed without this decision.
  * **Sharing System:** When the user shares their "Saigon Trip Album," what is the thumbnail image used? It's the "Best Shot." This decision impacts how others (friends, family) perceive the trip.

-----

## 📈 2) Clarify Objectives

The overall objective is to automatically inspect a group of photos and select a single representative photo with the highest technical quality and aesthetic appeal.

### 01: Maximize Technical Quality

This objective addresses your "select sharpest photo" example.

1.  **1.1 (Technical Score):** The chosen "Best Shot" must have the highest composite technical score (e.g., a `quality_score` combining `blur_score`, `brightness`, `exposure`) in the cluster.
2.  **1.2 (Absolute Exclusion):** Must **100%** exclude any photos flagged as "junk" (from 4.2, if any) or photos with extremely low technical scores from the candidate list.

### 02: Maximize Relevance & Aesthetics

This is the advanced goal, beyond just "sharpest photo."

1.  **2.1 (Face Priority):** If a cluster contains both landscapes and people, the system should be able to prioritize photos with clear, non-blinking faces (if that's the album's goal).
2.  **2.2 (Representativeness):** The chosen photo should represent the cluster's content. (e.g., the "Best Shot" for the "Notre Dame Cathedral" cluster should contain the cathedral, not just a close-up selfie that blocks the view).

### 03: Maximize Performance

1.  **3.1 (Decision Speed):** The process of scoring (if not already done) and comparing to select a "Best Shot" from a 50-photo cluster must take **\< 1 second**.

-----

## 📥 3) Define Inputs and Expected Outputs

### A. Inputs

1.  **Primary Input:**
      * A **Photo Cluster**: This is a `list` of photo objects. (e.g., `[imgA, imgB, imgC, ..., imgZ]`).
2.  **Required Data per Photo:**
      * Each photo object in the `list` *must* contain **pre-computed scores**.
      * e.g., `{ id: 'imgA', blur_score: 500, brightness_score: 90, face_count: 0 }`, `{ id: 'imgB', blur_score: 450, brightness_score: 85, face_count: 2 }`

### B. Expected Outputs

1.  **Primary Output:**
      * **A Single Photo Object**: The photo object identified as the "Best Shot" (e.g., `imgA`).
2.  **Supporting Output:**
      * The system may *update* the cluster list, flagging the chosen photo.
      * e.g., `imgA.is_best_shot = True`

-----

## 🛠️ 4) Solution & Tools (How?)

How and what tools to use to select the "Best Shot" from a cluster?

**Assumption:** As stated in Constraints (section 5.4), all scores (`blur_score`, `brightness_score`, `face_count`) were pre-computed in an earlier phase (e.g., 4.2) and are stored with the photo object. Phase 4.4.1 does **NOT** run CV; it only **compares** existing numbers.

### 1\. Tools

  * **Programming Language:** **Python** is the ideal choice for this.
  * **Libraries (for *previous* score calculation):**
      * **OpenCV (Python):** Used to calculate technical scores.
          * `cv2.Laplacian(image).var()`: To calculate `blur_score` (sharpness).
          * `cv2.mean(gray_image)[0]`: To calculate `brightness`.
      * **MediaPipe / Dlib (Python):** Used to detect faces (`face_count`) and features (e.g., eyes open/closed).

### 2\. Logic (How-to)

Function 4.4.1 is essentially a **scoring and ranking function**.

#### Method 1: Simple Logic (Per "select sharpest photo" example)

This is the most basic solution, based on a single metric.

```python
def select_best_by_blur(photo_cluster):
    """
    Selects the photo with the highest sharpness (blur_score).
    Assumes each photo is a dict with a 'blur_score' key.
    """
    if not photo_cluster:
        return None
        
    # max() with a key lambda is the most efficient way
    best_shot = max(photo_cluster, key=lambda photo: photo.get('blur_score', 0))
    return best_shot
```

#### Method 2: Composite Score Logic

This is a more realistic solution, balancing multiple objectives (Quality, Faces).

```python
def calculate_composite_score(photo):
    """
    Calculates a "composite quality" score for a single photo.
    The weights need to be tuned.
    """
    # Get scores, default to 0 if missing
    blur = photo.get('blur_score', 0)
    brightness = photo.get('brightness_score', 0) # Assumes normalized (e.g., 0-100)
    faces = photo.get('face_count', 0)
    
    # === Weights ===
    # Prioritize sharpness
    WEIGHT_BLUR = 0.5 
    # Prioritize brightness
    WEIGHT_BRIGHTNESS = 0.3
    # Prioritize photos with people (if present)
    WEIGHT_HAS_FACES = 0.2
    
    # Calculate score
    # Normalize blur score (e.g., assume max blur is 1000)
    normalized_blur = min(blur / 1000, 1.0) * 100
    
    # Bonus if faces are present
    face_bonus = 100 if faces > 0 else 0 
    
    final_score = (normalized_blur * WEIGHT_BLUR) + \
                  (brightness * WEIGHT_BRIGHTNESS) + \
                  (face_bonus * WEIGHT_HAS_FACES)
                  
    return final_score

def select_best_shot_composite(photo_cluster):
    """
    Selects the photo with the highest composite score.
    """
    if not photo_cluster:
        return None
        
    best_shot = max(photo_cluster, key=calculate_composite_score)
    return best_shot
```

**Solution:** Logic 4.4.1 will be a function (like `select_best_shot_composite`) that runs on each photo cluster provided by Phase 4.3.

-----

## 🚧 5) State Constraints

Barriers that make building this `select_best_shot` function difficult.

### 1\. Subjectivity Constraint

  * **This is the BIGGEST constraint.** "Best" is a completely subjective concept.
  * **Technical vs. Emotional Conflict:**
      * **Example:** The algorithm (4.4.1) will select `imgA` (sharp, well-lit) as the "Best Shot."
      * But the user might *prefer* `imgB`, which is *slightly blurry* but captures a moment of everyone laughing.
      * Your "select sharpest photo" function will fail to capture *emotional meaning*, which is the most important thing in a memory album.

### 2\. Algorithm Constraints

  * **Bias of "Scores":**
      * A simple `quality_score` (based only on sharpness + brightness) is not enough.
      * A photo of a textbook page will have a *perfect* `blur_score` (sharpness) and `brightness`, but it's a terrible "Best Shot."
      * The algorithm needs more complex scores (e.g., `aesthetic_score`, `composition_score`) which are very expensive and difficult to calculate accurately.

### 3\. Data Dependency

  * Function `select_best_shot` (4.4.1) is completely **dependent** on the quality of the scores (`blur_score`, etc.) calculated in the previous phase.
  * The "Garbage In, Garbage Out" principle applies perfectly: If the input scores are wrong, the "Best Shot" choice will also be wrong.

### 4\. System Design Constraints

  * **Pre-computation vs. On-the-fly:** To ensure Speed (Objective 3.1), all scores (sharpness, brightness, face count) **must** be calculated *once* (perhaps in Phase 4.2) and stored.
  * Function 4.4.1 should not *re-calculate* sharpness. It should only *compare* existing scores. This is an architectural constraint on the entire system.