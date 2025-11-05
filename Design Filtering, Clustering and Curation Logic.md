s# Design Filtering

> **Bối cảnh vấn đề (Problem Context):**
>
> Một khách du lịch (Tourist) vừa kết thúc chuyến đi ("Giai đoạn After"). Họ mở thư viện ảnh và thấy một mớ hỗn độn 500 tấm ảnh.
>
> Vấn đề không phải là ảnh hỏng (mờ/tối), mà là thư viện bị "rối" bởi rất nhiều **ảnh rác (Junk Photos)**: 3 ảnh trùng hệt nhau, 15 ảnh chụp liên tiếp (bursts) gần như y hệt, 5 ảnh chụp màn hình (screenshots), 2 ảnh hóa đơn, và 1 ảnh vô tình chụp xuống đất.
>
> Sự mệt mỏi khi phải tự mình xem và xóa 500 tấm ảnh này là một rào cản tâm lý. Họ cần một trợ lý tự động "dọn dẹp" mớ hỗn độn này, chỉ để lại những bức ảnh **có ý nghĩa** (meaningful) làm nguyên liệu cho giai đoạn tiếp theo (Gom cụm).

-----

## 🎯 1) Identify Stakeholders (Xác định các bên liên quan)

  * **Tourist (Người dùng cuối):** Người trực tiếp chịu đựng "sự bừa bộn". Họ muốn thư viện sạch sẽ, nhưng lại **sợ hãi** việc hệ thống xóa nhầm một bức ảnh "trông giống" ảnh rác nhưng thực ra là một kỷ niệm (ví dụ: xóa một bức ảnh trong loạt burst mà họ cười đẹp nhất).
  * **Hệ thống Gom cụm (Clustering System):** "Nạn nhân" của dữ liệu bẩn. Nếu không lọc, hệ thống sẽ tạo ra các cụm vô nghĩa (ví dụ: một cụm 15 ảnh burst, một cụm 5 ảnh chụp màn hình), làm loãng kết quả "câu chuyện".
  * **Nhà cung cấp Dịch vụ (Platform):** Muốn tiết kiệm chi phí lưu trữ đám mây. Việc lọc ảnh rác (đặc biệt là trùng lặp) giúp giảm đáng kể dung lượng lưu trữ.

-----

## 📈 2) Clarify Objectives (Làm rõ Mục tiêu)

Mục tiêu tổng quát là tự động phân loại và đề xuất loại bỏ các ảnh không có giá trị nội dung (ảnh rác), nhằm tối đa hóa sự liên quan của thư viện ảnh và giảm thiểu nỗ lực của người dùng.

### 01: Tối đa hóa Hiệu quả Dọn dẹp (Cleaning Efficiency)

1.  **1.1 (Phát hiện Trùng lặp):** Tự động xác định và đề xuất xóa **100%** các ảnh trùng lặp tuyệt đối (cùng hash).
2.  **1.2 (Phát hiện Rác Nội dung):** Tự động xác định và đề xuất xóa **\> 95%** các ảnh "rác" rõ ràng (ví dụ: `screenshot`, `hóa_đơn`, `tài_liệu`).
3.  **1.3 (Xử lý Chụp liên tiếp):** Tự động nhóm các ảnh chụp liên tiếp (bursts/near-duplicates) và đề xuất giữ lại chỉ 1-2 ảnh đại diện "tốt nhất".

### 02: Tối đa hóa Sự Tin cậy (Trust & Accuracy)

Đây là mục tiêu quan trọng nhất, ưu tiên hơn cả việc dọn dẹp sạch 100%.

1.  **2.1 (Tỷ lệ Xóa nhầm - False Positive):** Tỷ lệ hệ thống gắn cờ "rác" cho một bức ảnh kỷ niệm *có ý nghĩa* phải **\< 0.1%**.
2.  **2.2 (Tỷ lệ Phê duyệt Nhanh):** **\> 80%** người dùng chấp nhận "Xóa tất cả" các đề xuất của hệ thống mà không cần xem lại từng ảnh.

### 03: Tối ưu hóa Chất lượng Đầu ra (Downstream Quality)

1.  **3.1 (Độ tinh khiết của Cụm):** Kích hoạt Bộ lọc làm giảm số lượng "cụm rác" (ví dụ: cụm screenshot) ở Giai đoạn 4.3 (Gom cụm) ít nhất **80%**.

-----

## 📥 3) Define Inputs and Expected Outputs (Xác định Đầu vào và Đầu ra)

### A. Inputs (Đầu vào)

1.  **User Inputs (Đầu vào từ Người dùng):**
      * Một tập hợp (collection) ảnh chưa qua xử lý.
2.  **System Inputs (Đầu vào của Hệ thống):**
      * **Nội dung Ảnh (Image File):** Dữ liệu pixel thô.
      * **Siêu dữ liệu Ảnh (Image Metadata):**
          * `Timestamp` (rất quan trọng để phát hiện bursts).
          * `File Hash` (MD5/SHA256, để phát hiện trùng lặp 100%).
      * **Mô hình Phân loại (Models):** (Đã huấn luyện)
          * **Mô hình Phân loại Nội dung:** Để gán nhãn (ví dụ: `screenshot`, `hóa_đơn`, `tài_liệu`, `ảnh_thường`).
      * **Mô hình Tính đặc trưng (Models):**
          * **Feature Vectors (vd: CLIP, ResNet):** Để tìm các ảnh "gần giống hệt nhau" (near-duplicates) về mặt hình ảnh.
          * **Hàm Chấm điểm Chất lượng (Quality Scorer):** (Vẫn cần thiết) Dùng để chọn ảnh "đẹp nhất" (rõ nét nhất, bố cục tốt nhất) từ một loạt ảnh burst.

### B. Expected Outputs (Đầu ra Mong đợi)

1.  **Primary Output (Dữ liệu cho Hệ thống):**
      * Một **Danh sách Sạch (Clean List):** Chứa các ảnh đã vượt qua bộ lọc, sẵn sàng cho Giai đoạn 4.3 (Gom cụm).
2.  **Supporting Outputs (Thông tin cho Người dùng):**
      * Một **Danh sách Đề xuất Xóa (Deletion List):** Chứa các ảnh bị gắn cờ.
      * **Thẻ Lý do (Reason Tag):** Cực kỳ quan trọng để xây dựng lòng tin. (Ví dụ: `reason: "Trùng lặp"`, `reason: "Ảnh chụp màn hình"`, `reason: "Ảnh chụp liên tiếp"`).
      * **Giao diện Tương tác (Interactive UI):**
          * "Chúng tôi tìm thấy 5 ảnh chụp màn hình và 3 nhóm ảnh chụp liên tiếp. Bạn muốn dọn dẹp không?"
          * **(Quan trọng)** Giao diện "Chọn ảnh đẹp nhất" cho các nhóm ảnh chụp liên tiếp, cho phép người dùng ghi đè lựa chọn của AI.

-----

## 🛠️ 4) Solution & Tools (How?)

Làm thế nào và dùng công cụ gì để lọc 3 loại ảnh rác chính?

### 1\. Công cụ (Tools)

  * **Ngôn ngữ lập trình:** **Python**.
  * **Thư viện Hashing (cho 1.1):** `hashlib` (có sẵn trong Python) để tính toán `MD5` hoặc `SHA256` hash của file ảnh.
  * **Thư viện AI/CV (cho 1.2 & 1.3):**
      * **TensorFlow/Keras** hoặc **PyTorch:** Để chạy các mô hình AI.
      * **OpenCV:** Để tính điểm chất lượng (độ nét) cho ảnh burst.
      * **Pillow (PIL):** Để xử lý ảnh cơ bản (mở, resize) trước khi đưa vào mô hình.

### 2\. Logic (How-to)

Một pipeline (quy trình) xử lý sẽ chạy qua 3 bước:

#### Bước 1: Lọc Trùng lặp (Mục tiêu 1.1)

  * **Logic:** Dùng **Hashing**.
  * **Cách làm:**
    1.  Tạo một `set` rỗng tên là `seen_hashes`.
    2.  Duyệt qua từng ảnh.
    3.  Tính `file_hash` (ví dụ: MD5) cho file ảnh.
    4.  Nếu `file_hash` đã có trong `seen_hashes`, đánh dấu ảnh này là `junk_reason: "Trùng lặp"`.
    5.  Nếu không, thêm `file_hash` vào `seen_hashes`.
  * **Kết quả:** Loại bỏ 100% các file giống hệt nhau.

#### Bước 2: Lọc Rác Nội dung (Mục tiêu 1.2)

  * **Logic:** Dùng **Image Classification**.
  * **Cách làm:**
    1.  Lấy các ảnh *chưa* bị đánh dấu là trùng lặp.
    2.  Sử dụng một mô hình phân loại ảnh (ví dụ: **MobileNetV2**, nhanh và nhẹ) đã được huấn luyện để nhận diện các lớp như `screenshot`, `receipt` (hóa đơn), `document`, và `normal_photo`.
    3.  Cho từng ảnh chạy qua mô hình.
    4.  Nếu dự đoán của mô hình là `screenshot` hoặc `receipt` với độ tự tin \> 95%, đánh dấu ảnh là `junk_reason: "Ảnh chụp màn hình"`.
  * **Kết quả:** Loại bỏ các ảnh rác có nội dung rõ ràng.

#### Bước 3: Xử lý Chụp liên tiếp (Mục tiêu 1.3)

  * **Logic:** Kết hợp **Gom cụm theo Thời gian** và **Chấm điểm Chất lượng**.
  * **Cách làm:**
    1.  Lấy các ảnh còn lại (đã qua Bước 1 và 2).
    2.  **Sắp xếp** toàn bộ ảnh theo `timestamp`.
    3.  Duyệt qua danh sách đã sắp xếp, tìm các "cụm thời gian" (Time Bursts) - ví dụ: các nhóm ảnh được chụp cách nhau dưới 2 giây.
    4.  **Đối với mỗi Cụm thời gian (Burst Group):**
          * (Tùy chọn, nâng cao): Tính **Perceptual Hash** (ví dụ: `pHash`) cho các ảnh trong cụm. Nếu pHash quá khác nhau, chúng không phải là burst (ví dụ: 1 ảnh selfie, 1 ảnh phong cảnh).
          * **Chấm điểm chất lượng:** Dùng **OpenCV** (`cv2.Laplacian(img).var()`) để tính `blur_score` (độ nét) cho MỌI ảnh trong cụm.
          * **Chọn Best Shot:** Giữ lại bức ảnh có `blur_score` cao nhất.
          * Đánh dấu tất cả các ảnh còn lại trong cụm là `junk_reason: "Ảnh chụp liên tiếp"`.

-----

## 🚧 5) State Constraints (Phân tích Ràng buộc)

Các rào cản khiến việc xây dựng bộ lọc "ảnh rác" này trở nên khó khăn.

### 1\. Ràng buộc về Ngữ nghĩa (Semantic Ambiguity)

  * **Đây là ràng buộc LỚN NHẤT.** "Rác" là một khái niệm chủ quan.
  * **Ví dụ 1:** Ảnh chụp màn hình (screenshot) bản đồ đường đi là "rác" sau chuyến đi, *nhưng* ảnh chụp màn hình tin nhắn vui vẻ là một "kỷ niệm".
  * **Ví dụ 2:** Ảnh chụp menu nhà hàng hoặc hóa đơn có thể là "rác", *nhưng* cũng có thể là một phần "nhật ký" chuyến đi mà người dùng muốn giữ lại.
  * Hệ thống không thể hiểu được *ý định* (intent) của người dùng khi họ chụp bức ảnh đó.

### 2\. Ràng buộc về Kỹ thuật & Thuật toán (Algorithm)

  * **Lựa chọn ảnh "Tốt nhất" (Best Photo Selection):** Khi xử lý 10 ảnh burst (Gần giống hệt), việc chọn ra ảnh "tốt nhất" là rất khó. "Tốt nhất" có thể là: rõ nét nhất (dễ), không ai nhắm mắt (khó), mọi người đều cười (rất khó), bố cục đẹp nhất (cực kỳ khó).
  * **Phân biệt Near-Duplicate và Ảnh-khác-nhau:** Rất khó để đặt ngưỡng (threshold) phân biệt "hai ảnh chụp liên tiếp" (gần giống) và "hai ảnh chụp cùng một địa điểm nhưng ở góc khác nhau" (khác nhau).

### 3\. Ràng buộc về Dữ liệu (Data)

  * **Dữ liệu "Rác" rất đa dạng:** Ảnh "rác" là một mục tiêu động. Hôm nay là ảnh hóa đơn, ngày mai là memes, ngày kia là ảnh chụp màn hình từ một ứng dụng mới. Mô hình phân loại nội dung phải được cập nhật liên tục.

### 4\. Ràng buộc về Người dùng & Trải nghiệm (User & Trust)

  * **Nỗi sợ Bị xóa nhầm (False Positives):** Như đã nêu, người dùng thà chịu bừa bộn còn hơn mất đi kỷ niệm. Hệ thống không bao giờ được phép *tự động xóa* mà không hỏi ý kiến, điều này làm giảm tính "tự động" của quy trình.

-----

-----

# Design Clustering

> **Bối cảnh vấn đề (Problem Context):**
>
> Sau khi Giai đoạn 4.2 (Lọc) hoàn thành, người dùng (Tourist) có một "Danh sách Sạch" (Clean List) gồm, ví dụ, 300 bức ảnh "tốt".
>
> Vấn đề hiện tại là danh sách này vẫn **phẳng (flat)**. Nó chỉ là một cuộn (scroll) dài vô tận 300 bức ảnh xếp theo thời gian. Người dùng không có cách nào để "lướt" qua chuyến đi của họ một cách có ý nghĩa.
>
> Họ không thể thấy "Ngày 1 chúng ta đã làm gì?" hoặc "Những ảnh chụp ở bảo tàng đâu?". Sự mệt mỏi của việc "dọn rác" (4.2) giờ được thay thế bằng sự mệt mỏi của việc "tìm kiếm" trong một danh sách sạch nhưng quá dài.
>
> Họ cần hệ thống tự động **phân nhóm (group)** 300 bức ảnh này thành các "chương" (chapters) hoặc "cảnh" (scenes) có ý nghĩa, dựa trên bối cảnh chúng được chụp (Thời gian và Vị trí).

-----

## 🎯 1) Identify Stakeholders (Xác định các bên liên quan)

  * **Tourist (Người dùng cuối):** Người trực tiếp hưởng lợi. Họ muốn xem lại chuyến đi của mình dưới dạng một "câu chuyện" được tổ chức tốt (VD: "Ngày 1: Tham quan Nhà thờ, Ăn trưa tại Quận 1"), chứ không phải một cuộn ảnh dài.
  * **Hệ thống Tạo Câu chuyện (Story Generation System) (Giai đoạn 4.4/4.5):** Đây là "khách hàng" nội bộ. Nó *cần* dữ liệu đầu vào có cấu trúc. Nó không thể chọn "Ảnh bìa cho Ngày 1" (4.5.1) nếu nó không biết "Ngày 1" chứa ảnh nào (4.3.1). Nó không thể đặt tên "Chuyến thăm Bảo tàng" nếu nó không biết các ảnh nào thuộc về "Cụm Bảo tàng" (4.3.2).
  * **API Dịch vụ (Service APIs):** (VD: Google Maps, Nominatim). Các dịch vụ này được sử dụng trong 4.3.3 để cung cấp tên cho các cụm GPS. Họ quan tâm đến số lượng lệnh gọi API (có thể tốn chi phí).

-----

## 📈 2) Clarify Objectives (Làm rõ Mục tiêu)

Mục tiêu tổng quát là biến một danh sách ảnh phẳng, đã được lọc, thành một cấu trúc dữ liệu giàu ngữ cảnh, được tổ chức theo hai trục chính (Thời gian và Vị trí) để làm nền tảng cho việc tạo album tự động.

### 01: Tổ chức theo Trục Thời gian (Time Axis - 4.3.1)

Đây là cấu trúc điều hướng chính, giống như các "Chương" của cuốn sách.

1.  **1.1 (Phân chia tuyệt đối):** 100% ảnh trong `Clean List` phải được gán vào một nhóm "Ngày X" (VD: "Ngày 1", "Ngày 2").
2.  **1.2 (Ngưỡng ngày hợp lý):** Việc chuyển ngày phải hợp lý. (VD: "Ngày 1" được xác định bằng ngày của bức ảnh đầu tiên, chứ không phải ngày 1 của tháng).

### 02: Tổ chức theo Trục Vị trí (Location Axis - 4.3.2)

Đây là cấu trúc ngữ nghĩa, giống như các "Cảnh" trong một Chương.

1.  **2.1 (Độ chính xác của Cụm):** Các cụm GPS được tạo ra phải "đúng" theo cảm nhận của con người. Các ảnh chụp tại cùng một địa điểm (VD: trong vòng 100m) phải thuộc cùng một cụm.
2.  **2.2 (Độ bao phủ):** \> 90% ảnh *có dữ liệu GPS hợp lệ* phải được gán vào một cụm vị trí (không phải "nhiễu" - cluster -1).
3.  **2.3 (Xử lý Nhiễu):** Hệ thống phải mạnh mẽ (robust) trước các điểm dữ liệu GPS "nhiễu" (VD: ảnh chụp trên xe bus, ảnh bị trôi GPS). DBSCAN làm tốt việc này bằng cách gán chúng nhãn `-1`.

### 03: Làm giàu Ngữ nghĩa (Semantic Enrichment - 4.3.3)

Làm cho các cụm vị trí trở nên hữu ích với con người.

1.  **3.1 (Tính hữu ích của Tên):** \> 90% các cụm vị trí (VD: có \> 3 ảnh) phải được gán một tên *có ý nghĩa* (VD: "Nhà thờ Đức Bà" hoặc "Khu vực đường Đồng Khởi") thay vì "Cụm 0" hoặc tọa độ `(10.77, 106.69)`.
2.  **3.2 (Tốc độ đặt tên):** Thời gian gọi API để đặt tên cho mỗi cụm phải nhanh (VD: \< 2 giây) để không làm chậm toàn bộ quá trình xử lý.

-----

## 📥 3) Define Inputs and Expected Outputs (Xác định Đầu vào và Đầu ra)

### A. Inputs (Đầu vào)

1.  **Primary Input (Đầu vào chính):**
      * `Clean List`: Một danh sách (list) các đối tượng (object) ảnh đã qua Giai đoạn 4.2.
2.  **Required Data per Photo (Dữ liệu bắt buộc cho mỗi ảnh):**
      * `image_id`: (Định danh duy nhất)
      * `timestamp`: (Chuỗi ISO 8601, bắt buộc cho 4.3.1)
      * `location`: (Một tuple `(latitude, longitude)`, bắt buộc cho 4.3.2)
3.  **System Parameters (Tham số hệ thống):**
      * Cho 4.3.2 (DBSCAN): `eps` (bán kính gom cụm, VD: 100 mét) và `min_samples` (số ảnh tối thiểu, VD: 3 ảnh).
      * Cho 4.3.3: `API Key` (Khóa API cho dịch vụ Reverse Geocoding).

### B. Expected Outputs (Đầu ra Mong đợi)

1.  **Output 1 (cho 4.3.1): Cấu trúc theo Ngày (Day Structure)**
      * Một cấu trúc dữ liệu (VD: dictionary/map) ánh xạ Tên Ngày với danh sách ảnh.
      * `DayClusters = { "Ngày 1": [imgA, imgB, ...], "Ngày 2": [imgC, ...] }`
2.  **Output 2 (cho 4.3.2): Gán nhãn Vị trí (Location Labels)**
      * Đây *không phải* là một cấu trúc mới, mà là **sự cập nhật** cho `Clean List`.
      * Mỗi đối tượng ảnh trong `Clean List` giờ đây có thêm một thuộc tính: `cluster_id`.
      * `CleanList = [ {id: imgA, ts: ..., loc: ..., cluster_id: 0}, {id: imgB, ts: ..., loc: ..., cluster_id: 0}, {id: imgC, ts: ..., loc: ..., cluster_id: -1} ]`
3.  **Output 3 (cho 4.3.3): Ánh xạ Tên Cụm (Cluster Name Map)**
      * Một cấu trúc dữ liệu (VD: dictionary/map) ánh xạ `cluster_id` với tên do con người đọc được.
      * `ClusterNames = { 0: "Khu vực Nhà thờ Đức Bà", 1: "Bảo tàng Chứng tích Chiến tranh", ... }`

-----

## 🛠️ 4) Solution & Tools (How?)

Làm thế nào và dùng công cụ gì để gom cụm theo Thời gian và Vị trí?

### 1\. Công cụ (Tools)

  * **Ngôn ngữ lập trình:** **Python**.
  * **Thư viện (cho 4.3.1):** `datetime` và `collections.defaultdict` (có sẵn trong Python).
  * **Thư viện (cho 4.3.2):**
      * **Scikit-learn (`sklearn`):** Cụ thể là `sklearn.cluster.DBSCAN`.
      * **NumPy:** Để chuẩn bị mảng tọa độ cho `sklearn`.
  * **Thư viện (cho 4.3.3):**
      * **Geopy:** Một thư viện Python để truy cập các dịch vụ Geocoding.
      * **API Dịch vụ:** **Nominatim (OpenStreetMap)** (miễn phí) hoặc **Google Maps Geocoding API** (trả phí, chính xác hơn).

### 2\. Logic (How-to)

#### Hàm 4.3.1: Gom Cụm theo Ngày

  * **Logic:** Phân nhóm dựa trên chênh lệch ngày (date delta).
  * **Cách làm:**
    1.  Duyệt qua `Clean List`, chuyển đổi `timestamp` (string) thành `datetime` objects.
    2.  **Sắp xếp** `Clean List` theo `datetime` object.
    3.  Lấy ngày bắt đầu: `start_date = clean_list[0].datetime_obj.date()`.
    4.  Tạo một `defaultdict(list)`.
    5.  Duyệt qua danh sách đã sắp xếp, với mỗi ảnh:
          * Tính `day_number = (photo.datetime_obj.date() - start_date).days + 1`.
          * Gán ảnh vào dict: `day_clusters[f"Ngày {day_number}"].append(photo)`.
    6.  Trả về `day_clusters`.

#### Hàm 4.3.2: Gom Cụm theo GPS (DBSCAN)

  * **Logic:** Chạy DBSCAN trên tọa độ cầu (haversine).
  * **Cách làm:**
    1.  Lọc `Clean List` để chỉ lấy các ảnh có dữ liệu GPS.
    2.  Tạo một mảng NumPy `coords` chứa các `(lat, lon)` từ các ảnh này.
    3.  **Chuyển đổi:** Dùng `np.radians(coords)` để chuyển toàn bộ tọa độ sang **radians** (bắt buộc cho `haversine`).
    4.  **Chuyển đổi Epsilon:** `eps_in_radians = eps_meters / 6371000` (với 6371000 là bán kính Trái Đất bằng mét).
    5.  Khởi tạo DBSCAN: `db = DBSCAN(eps=eps_in_radians, min_samples=3, metric='haversine', algorithm='ball_tree')`.
    6.  Chạy gom cụm: `db.fit(radians_coords)`.
    7.  Lấy nhãn: `labels = db.labels_` (sẽ là `-1` cho nhiễu, `0`, `1`, `2`... cho các cụm).
    8.  Duyệt qua danh sách ảnh và `labels`, gán `photo['cluster_id'] = label` tương ứng.

#### Hàm 4.3.3: Đặt tên Cụm

  * **Logic:** Dùng Reverse Geocoding trên tọa độ trung tâm (centroid) của cụm.
  * **Cách làm:**
    1.  Tạo một `defaultdict(list)` để nhóm các ảnh theo `cluster_id` (từ 4.3.2, bỏ qua `-1`).
    2.  Tạo một `dict` rỗng `cluster_name_map`.
    3.  Khởi tạo API (ví dụ: `geolocator = Nominatim(user_agent="my-app")`).
    4.  Duyệt qua các cụm đã nhóm: `for cluster_id, photos_in_cluster in grouped_clusters.items():`
          * Tính tọa độ trung tâm (centroid): `mean_lat = mean([p.lat for p in photos_in_cluster])`, tương tự cho `mean_lon`.
          * Gọi API: `location = geolocator.reverse((mean_lat, mean_lon), language='vi')`.
          * Lấy tên (ví dụ: `location.raw.get('name')` hoặc một phần của `location.address`).
          * Lưu tên: `cluster_name_map[cluster_id] = clean_name`.
    5.  Trả về `cluster_name_map`.

-----

## 🚧 5) State Constraints (Phân tích Ràng buộc)

Các rào cản khiến việc xây dựng bộ gom cụm này trở nên thách thức.

### 1\. Ràng buộc về Dữ liệu (Data Constraints)

  * **Dữ liệu GPS bị thiếu hoặc Kém:** Đây là ràng buộc **lớn nhất**.
      * **Trong nhà (Indoors):** Ảnh chụp trong bảo tàng, nhà hàng, khách sạn thường *không có* tín hiệu GPS. Những ảnh này sẽ không thể được gom cụm theo vị trí.
      * **Trôi GPS (GPS Drift):** Tín hiệu GPS ở khu vực đô thị (giữa các tòa nhà cao tầng) bị "nhảy" (drift). 10 bức ảnh chụp ở cùng một ngã tư có thể bị ghi nhận ở 10 vị trí cách nhau 50m. Điều này sẽ *phá vỡ* DBSCAN.

### 2\. Ràng buộc về Thuật toán (Algorithm Constraints)

  * **Độ nhạy của DBSCAN (4.3.2):**
      * Việc chọn tham số `eps` (bán kính) là cực kỳ quan trọng và khó khăn. `eps = 100m` có thể tốt ở trung tâm thành phố, nhưng quá *nhỏ* cho một khu du lịch trải rộng (VD: một bãi biển) và quá *lớn* cho một con phố (VD: gộp nhầm 3 cửa hàng khác nhau làm một).
  * **Vấn đề "Nửa đêm" (4.3.1):**
      * Logic "chia theo ngày" rất đơn giản nhưng có thể sai. Một bữa tiệc bắt đầu lúc 10 giờ tối (Ngày 1) và kết thúc lúc 2 giờ sáng (Ngày 2) là *một* sự kiện trong mắt người dùng, nhưng hàm 4.3.1 sẽ chia nó thành *hai* ngày, phá vỡ logic "câu chuyện".

### 3\. Ràng buộc về Dịch vụ & Chi phí (Service & Cost Constraints)

  * **Chi phí API (4.3.3):** Dịch vụ Reverse Geocoding (như Google Maps) tính phí theo mỗi lượt gọi. Nếu một chuyến đi tạo ra 50 cụm vị trí, hệ thống sẽ phải gọi 50 lần, tốn chi phí.
  * **Tính hữu ích của API (4.3.3):** API có thể trả về một cái tên "đúng" nhưng "vô dụng".
      * **Ví dụ 1 (Quá chung chung):** Trả về "Phường Bến Nghé, Quận 1" thay vì "Nhà thờ Đức Bà".
      * **Ví dụ 2 (Quá cụ thể):** Trả về "135 Đường Nam Kỳ Khởi Nghĩa" thay vì "Dinh Độc Lập".

-----

-----

# Design Curation Logic

> **Bối cảnh vấn đề (Problem Context):**
>
> Sau Giai đoạn 4.3 (Gom cụm), chúng ta đã có các nhóm ảnh (VD: "Ngày 1", "Khu vực Nhà thờ Đức Bà").
>
> Vấn đề là các cụm này vẫn còn **"béo" (fat)**. Cụm "Khu vực Nhà thờ Đức Bà" có thể chứa 50 bức ảnh. Đây là một sự cải tiến so với 300 ảnh (ở 4.3), nhưng vẫn quá nhiều.
>
> Khi người dùng (Tourist) hoặc hệ thống muốn xem "tóm tắt" của cụm này, họ bị **Tê liệt vì Lựa chọn (Choice Paralysis)**. Hệ thống cần tạo một "ảnh bìa" (cover photo) cho "chương" này của câu chuyện, nhưng nó không biết chọn ảnh nào trong 50 ảnh đó.
>
> Họ cần một "biên tập viên" (Curation Logic) tự động xem xét tất cả 50 ảnh và **tuyển chọn** ra một bức ảnh duy nhất, **tốt nhất (Best Shot)**, để làm đại diện cho toàn bộ cụm.

-----

## 🎯 1) Identify Stakeholders (Xác định các bên liên quan)

  * **Tourist (Người dùng cuối):** Người hưởng lợi chính. Họ muốn thấy bức ảnh *đẹp nhất* của họ được dùng làm ảnh bìa. Một "Best Shot" được chọn đúng (VD: ảnh selfie đẹp, ảnh phong cảnh nét) làm họ cảm thấy hài lòng. Một "Best Shot" bị chọn sai (VD: ảnh mờ, chụp lỗi) làm giảm giá trị của toàn bộ album.
  * **Hệ thống Tạo Album (Album Generation System):** "Khách hàng" nội bộ trực tiếp. Nó *cần* một `cover_image` để hiển thị trong giao diện tóm tắt album. Nó không thể tiếp tục nếu không có quyết định này.
  * **Hệ thống Chia sẻ (Sharing System):** Khi người dùng chia sẻ "Album chuyến đi Sài Gòn", bức ảnh thumbnail được dùng là gì? Đó chính là "Best Shot". Quyết định này ảnh hưởng đến cách người khác (bạn bè, gia đình) nhìn nhận về chuyến đi.

-----

## 📈 2) Clarify Objectives (Làm rõ Mục tiêu)

Mục tiêu tổng quát là tự động kiểm tra một nhóm ảnh và chọn ra một bức ảnh đại diện duy nhất có chất lượng kỹ thuật và tính thẩm mỹ cao nhất.

### 01: Tối đa hóa Chất lượng Kỹ thuật (Technical Quality)

1.  **1.1 (Điểm Kỹ thuật):** "Best Shot" được chọn phải có điểm kỹ thuật tổng hợp (ví dụ: `quality_score` kết hợp từ `blur_score`, `brightness`, `exposure`) cao nhất trong cụm.
2.  **1.2 (Loại trừ Tuyệt đối):** Phải **100%** loại bỏ các ảnh đã bị gắn cờ "rác" (từ 4.2) hoặc các ảnh có điểm kỹ thuật cực thấp ra khỏi danh sách ứng cử viên.

### 02: Tối đa hóa Sự liên quan & Thẩm mỹ (Relevance & Aesthetics)

1.  **2.1 (Ưu tiên Gương mặt):** Nếu cụm ảnh chứa cả phong cảnh và con người, hệ thống nên có khả năng ưu tiên ảnh có gương mặt rõ nét, không nhắm mắt.
2.  **2.2 (Tính Đại diện):** Ảnh được chọn nên đại diện cho nội dung của cụm.

### 03: Tối đa hóa Hiệu suất (Performance)

1.  **3.1 (Tốc độ Quyết định):** Quá trình chấm điểm (nếu chưa có) và so sánh để chọn "Best Shot" từ một cụm 50 ảnh phải mất **\< 1 giây**.

-----

## 📥 3) Define Inputs and Expected Outputs (Xác định Đầu vào và Đầu ra)

### A. Inputs (Đầu vào)

1.  **Primary Input (Đầu vào chính):**
      * Một **Cụm ảnh (Photo Cluster)**: Đây là một `list` các đối tượng ảnh. (VD: `[imgA, imgB, imgC, ..., imgZ]`).
2.  **Required Data per Photo (Dữ liệu bắt buộc cho mỗi ảnh):**
      * Mỗi đối tượng ảnh trong `list` *phải* chứa các **điểm số đã được tính toán trước** (pre-computed scores).
      * VD: `{ id: 'imgA', blur_score: 500, brightness_score: 90, face_count: 0 }`, `{ id: 'imgB', blur_score: 450, brightness_score: 85, face_count: 2 }`

### B. Expected Outputs (Đầu ra Mong đợi)

1.  **Primary Output (Đầu ra chính):**
      * **Một đối tượng ảnh duy nhất (Single Photo Object)**: Đối tượng ảnh được xác định là "Best Shot" (VD: `imgA`).
2.  **Supporting Output (Đầu ra hỗ trợ):**
      * Hệ thống có thể *cập nhật* danh sách cụm, gắn cờ cho ảnh được chọn.
      * VD: `imgA.is_best_shot = True`

-----

## 🛠️ 4) Solution & Tools (How?)

Làm thế nào và dùng công cụ gì để chọn ra "Best Shot" từ một cụm?

**Giả định:** Như đã nêu trong Ràng buộc (mục 5.4), tất cả các điểm số (`blur_score`, `brightness_score`, `face_count`) đã được tính toán ở giai đoạn trước (ví dụ 4.2) và được lưu trữ cùng với đối tượng ảnh. Giai đoạn 4.4.1 **KHÔNG** chạy CV, mà chỉ **so sánh** các con số đã có.

### 1\. Công cụ (Tools)

  * **Ngôn ngữ lập trình:** **Python** là lựa chọn lý tưởng cho việc này.
  * **Thư viện (để tính toán điểm *trước đó*):**
      * **OpenCV (Python):** Dùng để tính toán các điểm số kỹ thuật.
          * `cv2.Laplacian(image).var()`: Dùng để tính `blur_score` (độ nét).
          * `cv2.mean(gray_image)[0]`: Dùng để tính `brightness` (độ sáng).
      * **MediaPipe / Dlib (Python):** Dùng để phát hiện gương mặt (`face_count`) và các đặc điểm (ví dụ: mắt nhắm/mở).

### 2\. Logic (How-to)

Hàm 4.4.1 về cơ bản là một **hàm chấm điểm và xếp hạng (scoring and ranking function)**.

#### Cách 1: Logic Đơn giản (Theo VD "chọn ảnh nét nhất")

Đây là giải pháp cơ bản nhất, chỉ dựa trên một chỉ số.

```python
def select_best_by_blur(photo_cluster):
    """
    Chọn ảnh có điểm nét (blur_score) cao nhất.
    Giả định mỗi ảnh là một dict có key 'blur_score'.
    """
    if not photo_cluster:
        return None
        
    # max() với một key lambda là cách hiệu quả nhất
    best_shot = max(photo_cluster, key=lambda photo: photo.get('blur_score', 0))
    return best_shot
```

#### Cách 2: Logic Tổng hợp (Composite Score)

Đây là giải pháp thực tế hơn, cân bằng nhiều mục tiêu (Chất lượng, Gương mặt).

```python
def calculate_composite_score(photo):
    """
    Tính một điểm "chất lượng tổng hợp" cho một ảnh.
    Các trọng số (weights) cần được tinh chỉnh (tune).
    """
    # Lấy điểm, mặc định là 0 nếu thiếu
    blur = photo.get('blur_score', 0)
    brightness = photo.get('brightness_score', 0) # Giả sử đã chuẩn hóa (vd: 0-100)
    faces = photo.get('face_count', 0)
    
    # === Trọng số ===
    # Ưu tiên độ nét
    WEIGHT_BLUR = 0.5 
    # Ưu tiên độ sáng
    WEIGHT_BRIGHTNESS = 0.3
    # Ưu tiên ảnh có mặt người (nếu có)
    WEIGHT_HAS_FACES = 0.2
    
    # Tính điểm
    # Chuẩn hóa điểm blur (ví dụ: giả sử max blur là 1000)
    normalized_blur = min(blur / 1000, 1.0) * 100
    
    # Thưởng nếu có mặt người
    face_bonus = 100 if faces > 0 else 0 
    
    final_score = (normalized_blur * WEIGHT_BLUR) + \
                  (brightness * WEIGHT_BRIGHTNESS) + \
                  (face_bonus * WEIGHT_HAS_FACES)
                  
    return final_score

def select_best_shot_composite(photo_cluster):
    """
    Chọn ảnh có điểm tổng hợp cao nhất.
    """
    if not photo_cluster:
        return None
        
    best_shot = max(photo_cluster, key=calculate_composite_score)
    return best_shot
```

**Giải pháp:** Logic 4.4.1 sẽ là một hàm (như `select_best_shot_composite`) chạy trên mỗi cụm ảnh được cung cấp bởi Giai đoạn 4.3.

-----

## 🚧 5) State Constraints (Phân tích Ràng buộc)

Các rào cản khiến việc xây dựng hàm `select_best_shot` này trở nên khó khăn.

### 1\. Ràng buộc về Tính chủ quan (Subjectivity)

  * **Đây là ràng buộc LỚN NHẤT.** "Best" (Tốt nhất) là một khái niệm hoàn toàn chủ quan.
  * **Xung đột Kỹ thuật vs. Cảm xúc:**
      * **Ví dụ:** Thuật toán (4.4.1) sẽ chọn bức ảnh `imgA` (chụp rõ nét, đủ sáng) làm "Best Shot".
      * Nhưng người dùng có thể *thích* bức `imgB` hơn, vì nó *hơi mờ* nhưng ghi lại khoảnh khắc mọi người đang cười rộ lên.
      * Hàm "chọn ảnh nét nhất" của bạn sẽ thất bại trong việc nắm bắt *ý nghĩa cảm xúc* (emotional meaning), vốn là thứ quan trọng nhất trong một album kỷ niệm.

### 2\. Ràng buộc về Thuật toán (Algorithm)

  * **Sự phiến diện của "Điểm số":**
      * Một hàm `quality_score` đơn giản (chỉ dựa trên độ nét + độ sáng) là không đủ.
      * Một bức ảnh chụp một trang sách giáo khoa sẽ có `blur_score` (độ nét) và `brightness` (độ sáng) *hoàn hảo*, nhưng nó là một "Best Shot" tồi tệ.
      * Thuật toán cần các điểm số phức tạp hơn (VD: `aesthetic_score` - điểm thẩm mỹ, `composition_score` - điểm bố cục) mà việc tính toán chúng rất tốn kém và khó chính xác.

### 3\. Ràng buộc về Dữ liệu (Data Dependency)

  * Hàm `select_best_shot` (4.4.1) hoàn toàn **phụ thuộc** vào chất lượng của các điểm số (`blur_score`, v.v.) được tính toán ở giai đoạn trước.
  * Nguyên lý "Rác đầu vào, Rác đầu ra" (Garbage In, Garbage Out) được áp dụng triệt để: Nếu các điểm số đầu vào bị tính sai, "Best Shot" được chọn cũng sẽ sai.

### 4\. Ràng buộc về Thiết kế Hệ thống (System Design)

  * **Tính toán trước vs. Tức thời:** Để đảm bảo Tốc độ (Mục tiêu 3.1), tất cả các điểm số (độ nét, độ sáng, số gương mặt) **phải** được tính toán *một lần* (có thể là ở Giai đoạn 4.2) và được lưu trữ.
  * Hàm 4.4.1 không nên *tính toán* lại độ nét. Nó chỉ nên *so sánh* các điểm số đã có. Đây là một ràng buộc về kiến trúc thiết kế của toàn bộ hệ thống.