# Image Handling

## I. Receive and save image file temporarily

### 1. Goal
Create a mechanism that allows users to select an image from their device (or take a photo using their phone), then send that image to the backend server, where it is temporarily stored (for metadata extraction and AI recognition).

### 2. Decomposition
- Receive and save image file temporarily
  - Image upload interface
    - Allow user to take a photo directly.
    - Allow user to select from photo library.
    - Allow user to select from file system.
  - Preprocess the image before sending.
  - Send the image to Backend.
  - Backend receives the image.
  - Validate the file.
  - Temporarily store the image.
  - Send a response to the frontend.

| Problem                                                         | Description                                          | Solution Approach                                                                                                                  |
| ----------------------------------------------------------------| ---------------------------------------------------- | ----------------------------------------------------------------------------------------------------                               |
| **1. Image upload interface (Frontend)**                        | Allow users to select an image                       | Allow user to take a photo directly. <br> Allow user to select from photo library. <br> Allow user to select from file system.     |
| **2. Preview and validate the image before sending (Frontend)** | Get the file from input and show a preview if needed | Use JavaScript to read `event.target.files[0]` and `URL.createObjectURL()` for preview                                             |
| **3. Send the image to Backend**                                | Send the file via HTTP request                       | Use `FormData()` and send it using `fetch()` or `axios.post()` to an API endpoint like `/api/upload`                               |
| **4. Backend receives the image**                               | The server handles the uploaded file                 | In Node.js, use the `multer` library to receive and process file uploads                                                           |
| **5. Validate the file**                                        | Ensure the file has a valid format and size          | Check file extensions `.jpg`, `.png`, `.heic`, etc.                                                                                |
| **6. Temporarily store the image**                              | Save the file in a `/uploads/temp/` directory        | `multer` to automatically store the file or use `fs.writeFile()` manually                                                          |
| **7. Send a response to the frontend**                          | Notify upload status                                 | Return HTTP response (JSON) `{ status: "success", filename: "abc.jpg" }`                                                           |

| Sub-problem                                              | Description                                                             | Solution Approach                                                                                                                                                                                                                                                                    |
| -------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| **1.1. Allow user to take a photo directly (camera)**    | Allow users to open their phone camera or webcam to capture a new photo | Use the HTML tag `<input type="file" accept="image/*" capture="environment">` to trigger the default camera on mobile devices. <br> For web apps (React, Vue, etc.), use libraries like **react-webcam** to display a live preview and capture an image using `getScreenshot()`.     |
| **1.2. Allow user to select from photo library**         | Allow users to choose existing images from their device’s photo library | Use the same tag `<input type="file" accept="image/*">` (the operating system will show the option “Choose from gallery”). <br>                                                                                                                                                      |
| **1.3. Allow user to select from file system (desktop)** | Allow users to pick images from their computer or external storage      | Use `<input type="file" accept=".jpg,.jpeg,.png,.heic">`. <br>                                                                                                                                                                                                                       |




## II. Extract GPS from image's EXIF

### 1. Goal
Extract available EXIF metadata (mainly GPS information) from the image to assist computer vision in making faster and more accurate decisions.

### 2. Decomposition
- Extract GPS from image's EXIF
  - Request Location Permission
  - Read and extract GPS data
  - Convert coordinates
  - Send data to Computer Vision Module
  
| Problem                                                     | Description                                                                                                   | Solution Approach                                                                                                                                                                        |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **1. Request Location Permission (Geolocation Permission)** | When the user opens the web app or chooses “Take Photo”, the system requests access to the current location.  | Use the API `navigator.geolocation.getCurrentPosition()` to retrieve GPS coordinates from the browser. If the user denies the request, set a flag `no_gps_permission` to skip this step. |
| **2. Read and extract GPS data (if available)**             | Locate and read the `GPSLatitude` and `GPSLongitude` tags from the EXIF metadata.                             | Use libraries such as `exifr` or `exif-parser` in Node.js / JavaScript to parse the metadata.                                                                                            |
| **3. Convert coordinates**                                  | EXIF usually stores coordinates in `[degree, minute, second]` format.                                         | Write a conversion function or use the formula: (deg + min / 60 + sec / 3600) * (ref == 'S' \|\| ref == 'W' ? -1 : 1).                                                                   |
| **4. Send data to Computer Vision Module**                  | Send the location information (if available) along with the image to the AI model for recognition assistance. | Send data in JSON format: `{ lat: 10.7629, lng: 106.6823, image: <file> }` to the endpoint `/api/analyze`.                                                                               |


