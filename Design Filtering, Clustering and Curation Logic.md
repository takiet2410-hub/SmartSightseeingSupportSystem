##### Desing Filtering

> **Bối cảnh vấn đề (Problem Context):**
>
> Một khách du lịch (Tourist) vừa kết thúc chuyến đi ("Giai đoạn After"). Họ mở thư viện ảnh và thấy một mớ hỗn độn 500 tấm ảnh.
>
> Vấn đề không phải là ảnh hỏng (mờ/tối), mà là thư viện bị "rối" bởi rất nhiều **ảnh rác (Junk Photos)**: 3 ảnh trùng hệt nhau, 15 ảnh chụp liên tiếp (bursts) gần như y hệt, 5 ảnh chụp màn hình (screenshots), 2 ảnh hóa đơn, và 1 ảnh vô tình chụp xuống đất.
>
> Sự mệt mỏi khi phải tự mình xem và xóa 500 tấm ảnh này là một rào cản tâm lý. Họ cần một trợ lý tự động "dọn dẹp" mớ hỗn độn này, chỉ để lại những bức ảnh **có ý nghĩa** (meaningful) làm nguyên liệu cho giai đoạn tiếp theo (Gom cụm).

---

## 🎯 1) Identify Stakeholders (Xác định các bên liên quan)

* **Tourist (Người dùng cuối):** Người trực tiếp chịu đựng "sự bừa bộn". Họ muốn thư viện sạch sẽ, nhưng lại **sợ hãi** việc hệ thống xóa nhầm một bức ảnh "trông giống" ảnh rác nhưng thực ra là một kỷ niệm (ví dụ: xóa một bức ảnh trong loạt burst mà họ cười đẹp nhất).
* **Hệ thống Gom cụm (Clustering System):** "Nạn nhân" của dữ liệu bẩn. Nếu không lọc, hệ thống sẽ tạo ra các cụm vô nghĩa (ví dụ: một cụm 15 ảnh burst, một cụm 5 ảnh chụp màn hình), làm loãng kết quả "câu chuyện".
* **Nhà cung cấp Dịch vụ (Platform):** Muốn tiết kiệm chi phí lưu trữ đám mây. Việc lọc ảnh rác (đặc biệt là trùng lặp) giúp giảm đáng kể dung lượng lưu trữ.

---

## 📈 2) Clarify Objectives (Làm rõ Mục tiêu)

Mục tiêu tổng quát là tự động phân loại và đề xuất loại bỏ các ảnh không có giá trị nội dung (ảnh rác), nhằm tối đa hóa sự liên quan của thư viện ảnh và giảm thiểu nỗ lực của người dùng.

### 01: Tối đa hóa Hiệu quả Dọn dẹp (Cleaning Efficiency)
1.  **1.1 (Phát hiện Trùng lặp):** Tự động xác định và đề xuất xóa **100%** các ảnh trùng lặp tuyệt đối (cùng hash).
2.  **1.2 (Phát hiện Rác Nội dung):** Tự động xác định và đề xuất xóa **> 95%** các ảnh "rác" rõ ràng (ví dụ: `screenshot`, `hóa_đơn`, `tài_liệu`).
3.  **1.3 (Xử lý Chụp liên tiếp):** Tự động nhóm các ảnh chụp liên tiếp (bursts/near-duplicates) và đề xuất giữ lại chỉ 1-2 ảnh đại diện "tốt nhất".

### 02: Tối đa hóa Sự Tin cậy (Trust & Accuracy)
Đây là mục tiêu quan trọng nhất, ưu tiên hơn cả việc dọn dẹp sạch 100%.

1.  **2.1 (Tỷ lệ Xóa nhầm - False Positive):** Tỷ lệ hệ thống gắn cờ "rác" cho một bức ảnh kỷ niệm *có ý nghĩa* phải **< 0.1%**. (Ví dụ: không được phép xóa ảnh chụp menu nhà hàng nếu người dùng muốn giữ nó làm kỷ niệm).
2.  **2.2 (Tỷ lệ Phê duyệt Nhanh):** **> 80%** người dùng chấp nhận "Xóa tất cả" các đề xuất của hệ thống mà không cần xem lại từng ảnh (cho thấy sự tin tưởng cao).

### 03: Tối ưu hóa Chất lượng Đầu ra (Downstream Quality)
1.  **3.1 (Độ tinh khiết của Cụm):** Kích hoạt Bộ lọc làm giảm số lượng "cụm rác" (ví dụ: cụm screenshot) ở Giai đoạn 4.3 (Gom cụm) ít nhất **80%**.

---

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

---

## 🚧 4) State Constraints (Phân tích Ràng buộc)

Các rào cản khiến việc xây dựng bộ lọc "ảnh rác" này trở nên khó khăn.

### 1. Ràng buộc về Ngữ nghĩa (Semantic Ambiguity)
* **Đây là ràng buộc LỚN NHẤT.** "Rác" là một khái niệm chủ quan.
* **Ví dụ 1:** Ảnh chụp màn hình (screenshot) bản đồ đường đi là "rác" sau chuyến đi, *nhưng* ảnh chụp màn hình tin nhắn vui vẻ là một "kỷ niệm".
* **Ví dụ 2:** Ảnh chụp menu nhà hàng hoặc hóa đơn có thể là "rác", *nhưng* cũng có thể là một phần "nhật ký" chuyến đi mà người dùng muốn giữ lại.
* Hệ thống không thể hiểu được *ý định* (intent) của người dùng khi họ chụp bức ảnh đó.

### 2. Ràng buộc về Kỹ thuật & Thuật toán (Algorithm)
* **Lựa chọn ảnh "Tốt nhất" (Best Photo Selection):** Khi xử lý 10 ảnh burst (Gần giống hệt), việc chọn ra ảnh "tốt nhất" là rất khó. "Tốt nhất" có thể là: rõ nét nhất (dễ), không ai nhắm mắt (khó), mọi người đều cười (rất khó), bố cục đẹp nhất (cực kỳ khó).
* **Phân biệt Near-Duplicate và Ảnh-khác-nhau:** Rất khó để đặt ngưỡng (threshold) phân biệt "hai ảnh chụp liên tiếp" (gần giống) và "hai ảnh chụp cùng một địa điểm nhưng ở góc khác nhau" (khác nhau).

### 3. Ràng buộc về Dữ liệu (Data)
* **Dữ liệu "Rác" rất đa dạng:** Ảnh "rác" là một mục tiêu động. Hôm nay là ảnh hóa đơn, ngày mai là memes, ngày kia là ảnh chụp màn hình từ một ứng dụng mới. Mô hình phân loại nội dung phải được cập nhật liên tục.

### 4. Ràng buộc về Người dùng & Trải nghiệm (User & Trust)
* **Nỗi sợ Bị xóa nhầm (Fear of False Positives):** Như đã nêu, người dùng thà chịu bừa bộn còn hơn mất đi kỷ niệm. Hệ thống không bao giờ được phép *tự động xóa* mà không hỏi ý kiến, điều này làm giảm tính "tự động" của quy trình.

##### Desing Clustering

> **Bối cảnh vấn đề (Problem Context):**
>
> Sau khi Giai đoạn 4.2 (Lọc) hoàn thành, người dùng (Tourist) có một "Danh sách Sạch" (Clean List) gồm, ví dụ, 300 bức ảnh "tốt".
>
> Vấn đề hiện tại là danh sách này vẫn **phẳng (flat)**. Nó chỉ là một cuộn (scroll) dài vô tận 300 bức ảnh xếp theo thời gian. Người dùng không có cách nào để "lướt" qua chuyến đi của họ một cách có ý nghĩa.
>
> Họ không thể thấy "Ngày 1 chúng ta đã làm gì?" hoặc "Những ảnh chụp ở bảo tàng đâu?". Sự mệt mỏi của việc "dọn rác" (4.2) giờ được thay thế bằng sự mệt mỏi của việc "tìm kiếm" trong một danh sách sạch nhưng quá dài.
>
> Họ cần hệ thống tự động **phân nhóm (group)** 300 bức ảnh này thành các "chương" (chapters) hoặc "cảnh" (scenes) có ý nghĩa, dựa trên bối cảnh chúng được chụp (Thời gian và Vị trí).

---

## 🎯 1) Identify Stakeholders (Xác định các bên liên quan)

* **Tourist (Người dùng cuối):** Người trực tiếp hưởng lợi. Họ muốn xem lại chuyến đi của mình dưới dạng một "câu chuyện" được tổ chức tốt (VD: "Ngày 1: Tham quan Nhà thờ, Ăn trưa tại Quận 1"), chứ không phải một cuộn ảnh dài.
* **Hệ thống Tạo Câu chuyện (Story Generation System) (Giai đoạn 4.4/4.5):** Đây là "khách hàng" nội bộ. Nó *cần* dữ liệu đầu vào có cấu trúc. Nó không thể chọn "Ảnh bìa cho Ngày 1" (4.5.1) nếu nó không biết "Ngày 1" chứa ảnh nào (4.3.1). Nó không thể đặt tên "Chuyến thăm Bảo tàng" nếu nó không biết các ảnh nào thuộc về "Cụm Bảo tàng" (4.3.2).
* **API Dịch vụ (Service APIs):** (VD: Google Maps, Nominatim). Các dịch vụ này được sử dụng trong 4.3.3 để cung cấp tên cho các cụm GPS. Họ quan tâm đến số lượng lệnh gọi API (có thể tốn chi phí).

---

## 📈 2) Clarify Objectives (Làm rõ Mục tiêu)

Mục tiêu tổng quát là biến một danh sách ảnh phẳng, đã được lọc, thành một cấu trúc dữ liệu giàu ngữ cảnh, được tổ chức theo hai trục chính (Thời gian và Vị trí) để làm nền tảng cho việc tạo album tự động.

### 01: Tổ chức theo Trục Thời gian (Time Axis - 4.3.1)
Đây là cấu trúc điều hướng chính, giống như các "Chương" của cuốn sách.
1.  **1.1 (Phân chia tuyệt đối):** 100% ảnh trong `Clean List` phải được gán vào một nhóm "Ngày X" (VD: "Ngày 1", "Ngày 2").
2.  **1.2 (Ngưỡng ngày hợp lý):** Việc chuyển ngày phải hợp lý. (VD: "Ngày 1" được xác định bằng ngày của bức ảnh đầu tiên, chứ không phải ngày 1 của tháng).

### 02: Tổ chức theo Trục Vị trí (Location Axis - 4.3.2)
Đây là cấu trúc ngữ nghĩa, giống như các "Cảnh" trong một Chương.
1.  **2.1 (Độ chính xác của Cụm):** Các cụm GPS được tạo ra phải "đúng" theo cảm nhận của con người. Các ảnh chụp tại cùng một địa điểm (VD: trong vòng 100m) phải thuộc cùng một cụm.
2.  **2.2 (Độ bao phủ):** > 90% ảnh *có dữ liệu GPS hợp lệ* phải được gán vào một cụm vị trí (không phải "nhiễu" - cluster -1).
3.  **2.3 (Xử lý Nhiễu):** Hệ thống phải mạnh mẽ (robust) trước các điểm dữ liệu GPS "nhiễu" (VD: ảnh chụp trên xe bus, ảnh bị trôi GPS). DBSCAN làm tốt việc này bằng cách gán chúng nhãn `-1`.

### 03: Làm giàu Ngữ nghĩa (Semantic Enrichment - 4.3.3)
Làm cho các cụm vị trí trở nên hữu ích với con người.
1.  **3.1 (Tính hữu ích của Tên):** > 90% các cụm vị trí (VD: có > 3 ảnh) phải được gán một tên *có ý nghĩa* (VD: "Nhà thờ Đức Bà" hoặc "Khu vực đường Đồng Khởi") thay vì "Cụm 0" hoặc tọa độ `(10.77, 106.69)`.
2.  **3.2 (Tốc độ đặt tên):** Thời gian gọi API để đặt tên cho mỗi cụm phải nhanh (VD: < 2 giây) để không làm chậm toàn bộ quá trình xử lý.

---

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

---

## 🚧 4) State Constraints (Phân tích Ràng buộc)

Các rào cản khiến việc xây dựng bộ gom cụm này trở nên thách thức.

### 1. Ràng buộc về Dữ liệu (Data Constraints)
* **Dữ liệu GPS bị thiếu hoặc Kém:** Đây là ràng buộc **lớn nhất**.
    * **Trong nhà (Indoors):** Ảnh chụp trong bảo tàng, nhà hàng, khách sạn thường *không có* tín hiệu GPS. Những ảnh này sẽ không thể được gom cụm theo vị trí.
    * **Trôi GPS (GPS Drift):** Tín hiệu GPS ở khu vực đô thị (giữa các tòa nhà cao tầng) bị "nhảy" (drift). 10 bức ảnh chụp ở cùng một ngã tư có thể bị ghi nhận ở 10 vị trí cách nhau 50m. Điều này sẽ *phá vỡ* DBSCAN.

### 2. Ràng buộc về Thuật toán (Algorithm Constraints)
* **Độ nhạy của DBSCAN (4.3.2):**
    * Việc chọn tham số `eps` (bán kính) là cực kỳ quan trọng và khó khăn. `eps = 100m` có thể tốt ở trung tâm thành phố, nhưng quá *nhỏ* cho một khu du lịch trải rộng (VD: một bãi biển) và quá *lớn* cho một con phố (VD: gộp nhầm 3 cửa hàng khác nhau làm một).
* **Vấn đề "Nửa đêm" (4.3.1):**
    * Logic "chia theo ngày" rất đơn giản nhưng có thể sai. Một bữa tiệc bắt đầu lúc 10 giờ tối (Ngày 1) và kết thúc lúc 2 giờ sáng (Ngày 2) là *một* sự kiện trong mắt người dùng, nhưng hàm 4.3.1 sẽ chia nó thành *hai* ngày, phá vỡ logic "câu chuyện".

### 3. Ràng buộc về Dịch vụ & Chi phí (Service & Cost Constraints)
* **Chi phí API (4.3.3):** Dịch vụ Reverse Geocoding (như Google Maps) tính phí theo mỗi lượt gọi. Nếu một chuyến đi tạo ra 50 cụm vị trí, hệ thống sẽ phải gọi 50 lần, tốn chi phí.
* **Tính hữu ích của API (4.3.3):** API có thể trả về một cái tên "đúng" nhưng "vô dụng".
    * **Ví dụ 1 (Quá chung chung):** Trả về "Phường Bến Nghé, Quận 1" thay vì "Nhà thờ Đức Bà".
    * **Ví dụ 2 (Quá cụ thể):** Trả về "135 Đường Nam Kỳ Khởi Nghĩa" thay vì "Dinh Độc Lập".
