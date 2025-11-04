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