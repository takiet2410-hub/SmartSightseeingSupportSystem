# After Service – Frontend Integration Flow

This document explains the **end-to-end workflow of the After Service** from a **Frontend developer perspective**.

The goal is to help a frontend engineer **understand the data flow, user interactions, and API usage** required to implement album generation and trip summary features correctly.

---

## 1. Overview

The **After Service** handles everything that happens **after a user finishes taking photos** during a trip.

It is responsible for:

* Uploading photos
* Generating albums automatically
* Allowing users to adjust album data (name, photos, location)
* Creating a final **Trip Summary** from albums

⚠️ Important architectural note:

* The After Service **does NOT connect to the During Service**
* All data comes **from the Frontend only**

---

## 2. High-Level User Flow

```text
User uploads photos
        ↓
Backend filters junk / low-quality images
        ↓
Photos are clustered into albums
        ↓
User reviews albums
        ↓
(Optional) User assigns or fixes album locations
        ↓
User generates Trip Summary
        ↓
Trip Summary is saved and displayed
```

---

## 3. Authentication Requirement

All After Service APIs require authentication.

Frontend must:

* Obtain JWT token from **Auth Service**
* Send token in request headers:

```
Authorization: Bearer <JWT_TOKEN>
```

---

## 4. Album Generation Flow

### 4.1 Upload Photos & Create Albums

**Endpoint**

```
POST /create-album
```

**Frontend responsibility**:

* Allow user to select multiple photos
* Send photos as `multipart/form-data`

**What backend does**:

* Uploads photos to Cloudinary
* Extracts metadata (time, GPS if available)
* Filters junk or low-quality images
* Groups photos into albums automatically

**Response (simplified)**:

```json
{
  "albums": [
    {
      "album_id": "uuid",
      "title": "Day 1 - City Center",
      "photos": [...],
      "has_gps": false
    }
  ]
}
```

**Frontend next step**:

* Render albums and photos
* Check `has_gps` to determine if location input is required

---

## 5. Album Management Flow

### 5.1 Rename Album

```
PATCH /albums/{album_id}/rename
```

Frontend:

* Provide text input for album name

---

### 5.2 Delete Album

```
DELETE /albums/{album_id}
```

Backend will:

* Remove database records
* Delete images from Cloudinary

---

### 5.3 Remove Photo from Album

```
DELETE /albums/{album_id}/photos/{photo_id}
```

Frontend:

* Triggered by a delete button per photo

---

## 6. Manual Location Assignment (Very Important)

### 6.1 When Is Manual Location Needed?

Frontend must ask user to select a location if:

* Album has no GPS data
* Album location is incorrect

This is detected by:

```text
album.has_gps === false
```

---

### 6.2 Address Search (OSM Geocoding)

**Endpoint**

```
POST /geocode/osm
```

**Request**

```json
{
  "address": "Chợ Bến Thành, TP Hồ Chí Minh"
}
```

**Response**

```json
[
  {
    "lat": 10.772544,
    "lon": 106.698313,
    "display_name": "Chợ Bến Thành, Quận 1, TP.HCM"
  }
]
```

Frontend should:

* Show search results
* Display marker on map
* Allow user to confirm or adjust location

⚠️ Do NOT trust geocoding result blindly.
User confirmation on map is required.

---

## 7. Trip Summary Generation Flow

### 7.1 Generate Trip Summary

**Endpoint**

```
POST /trip-summary
```

**Frontend sends**:

* Album data
* Manual locations (if any)

**Request example**

```json
{
  "album_data": {
    "albums": [
      {
        "album_id": "uuid",
        "title": "Day 1",
        "photos": [...]
      }
    ]
  },
  "manual_locations": [
    {
      "album_id": "uuid",
      "lat": 10.77,
      "lon": 106.69,
      "name": "Ho Chi Minh City"
    }
  ]
}
```

**Backend behavior**:

* Merges album GPS and manual locations
* Orders albums chronologically
* Creates a trip-level summary

---

## 8. View Trip Summary History

```
GET /summary/history
```

Frontend:

* Display list of past trip summaries
* Allow user to select or delete

---

## 9. Key Frontend Rules (Must Follow)

1. Always let user **confirm location on map**
2. Never assume geocoding result is correct
3. Album generation happens **before** trip summary
4. After Service works **independently** from During Service
5. JWT authentication is required for all requests

---

## 10. Simplified Mental Model for Frontend

```text
Photos → Albums → (Fix Locations) → Trip Summary
```

If frontend follows this model, integration will be correct.

---

## 11. Summary

This After Service is designed to be:

* Frontend-driven
* User-controlled
* Resilient to missing GPS data
* Independent from AI detection services

Following this document is sufficient to implement the complete frontend flow successfully.
