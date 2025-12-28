## CÁC THUẬT TOÁN ĐỒNG THUẬN ĐƠN GIẢN

**Bộ môn Công nghệ Tri thức**

---

## 1. Mục tiêu

Trong bài tập này, sinh viên sẽ hoàn thành các công việc cơ bản sau:

* Sử dụng gRPC hoặc libp2p để mô phỏng một mạng peer-to-peer.
* Hiểu và triển khai thuật toán đồng thuận RAFT trong mạng đã mô phỏng.
* Kiểm tra độ ổn định của hệ thống trong các tình huống lỗi như lỗi ở phía leader, lỗi ở phía thành viên, và tình huống mạng bị phân mảnh.
* (Điểm cộng) Tìm hiểu, đơn giản hóa và triển khai thuật toán Practical Byzantine Fault Tolerance (pBFT).
* Viết báo cáo chi tiết về những phần đã tìm hiểu được trong bài tập này, cùng với các mô tả chi tiết về phần chương trình sinh viên viết.

---

## 2. Yêu cầu cụ thể

### 2.1 Hiểu thuật toán RAFT

* Đọc bài báo: *In Search of an Understandable Consensus Algorithm*.
* Mô tả bằng hình ảnh: *RAFT Visualization*.
* Tìm hiểu:

  1. Làm thế nào RAFT đảm bảo tính nhất quán khi chuyển đổi leader?
  2. Hạn chế của RAFT khi xử lý các hành vi độc hại (malicious behavior)?

---

### 2.2 Cài đặt RAFT

**Cấu hình mạng:**

* Giả lập một mạng ngang hàng gồm tối thiểu 5 nút, mỗi nút hoạt động độc lập dưới dạng process, không yêu cầu hoạt động độc lập trên 5 máy.
* Sử dụng gRPC hoặc libp2p để giao tiếp giữa các nút.

**Các tính năng chính:**

1. **Chọn leader:**

   * Cài đặt tính năng RequestVote nhằm phục vụ bước chọn leader.
   * Tìm cách giải quyết các vấn đề xung đột trong quá trình chọn leader.

2. **Đồng bộ log:**

   * Triển khai tính năng đồng bộ dữ liệu giữa các nút, nhằm đảm bảo tính nhất quán của dữ liệu trong môi trường phân tán.

---

## Blockchain và ứng dụng – Bộ môn Công nghệ Tri thức

3. **Xử lý lỗi, xung đột:**

* Các lỗi từ phía leader, lỗi từ phía thành viên, và tình huống mạng bị phân mảnh:

  * (a) **Leader gặp lỗi:** Ngắt kết nối nút leader, lúc này mạng phải tự chọn ra được một leader mới.
  * (b) **Thành viên gặp lỗi:** Ngắt kết nối một (hoặc một số) nút thành viên và sau đó kết nối lại, đảm bảo log/dữ liệu được đồng bộ hóa, xác định ngưỡng thất bại (ví dụ, ngắt kết nối tối thiểu bao nhiêu thành viên thì không thể đồng bộ được nữa, tại sao).
  * (c) **Phân mảnh mạng:** Chia mạng thành hai nhóm và quan sát cách RAFT duy trì tính nhất quán (Có thể sử dụng một RPC đặc biệt, khi gửi một danh sách địa chỉ IP vào một nút bằng RPC đó, nút nhận sẽ tự động ngắt kết nối đến các địa chỉ đó).

4. **Cam kết (commit):**

* Lưu trữ các log đã commit vào cơ sở dữ liệu dạng key-value đơn giản.

---

### 2.3 Cài đặt pBFT (điểm cộng)

**Hiểu thuật toán pBFT:**

* Đọc bài báo: *Practical Byzantine Fault Tolerance*.
* Nắm rõ các giai đoạn của pBFT: Pre-prepare, Prepare, Commit.

**Cài đặt pBFT:**

1. Sử dụng lại mạng đã xây dựng ở phần trên, tạo một message đặc biệt để giả lập một block cho một mạng blockchain (chỉ cần có previous blockhash, blockhash, blockheight, các phần khác của block không quan trọng).

2. Cài đặt các tính năng chính của pBFT:

   * (a) **Pre-prepare:** Một nút sẽ gửi một block đến các nút khác (Sinh viên tự đề xuất cách chỉ định nút nào sẽ gửi).
   * (b) **Prepare:** Các nút xác minh block và gửi message đồng ý nếu block hợp lệ.
   * (c) **Commit:** Các nút commit block khi đạt đủ số message đồng ý.
   * (d) **Xử lý lỗi Byzantine:** Cài đặt một số nút đặc biệt thực hiện các hành vi gian lận, độc hại, gửi các message không đúng yêu cầu của protocol. Sinh viên phải đảm bảo các nút trung thực phát hiện và loại trừ được nút gian lận đó.

---

### 2.4 Báo cáo

Báo cáo không quá 10 trang A4, cần đảm bảo các phần sau:

1. **Mô tả RAFT:**
   Sinh viên cần tóm tắt lại thuật toán RAFT, cách hoạt động, mục đích, hạn chế. Tất cả các nguồn tham khảo cần được liệt kê cụ thể, và trích dẫn đúng đoạn nào lấy từ nguồn nào. Không có quy định về việc sử dụng các công cụ AI, nhưng phải đảm bảo yêu cầu trích dẫn đúng nguồn, đúng bài báo thật, và sinh viên cần hiểu rõ những gì mình viết trong báo cáo.

2. **So sánh RAFT và pBFT:**
   Sinh viên cần phải đọc và thực hiện phần so sánh này, việc cài đặt pBFT được tính điểm cộng, nhưng phần so sánh trong báo cáo là bắt buộc. Ngoài ra, các nhóm có cài đặt pBFT có thể viết so sánh chi tiết hơn, theo từng trường hợp lỗi, hoặc theo số lượng nút trong mạng.

3. **Mô tả chương trình đã cài đặt:**
   Viết chi tiết cách chạy chương trình đã cài đặt, cách thay đổi các tham số để điều chỉnh số lượng nút hoặc các thành phần khác (như cách setup nút động hại, cách tắt bật nút,...) trong chương trình của sinh viên.

4. **Tự đánh giá:**
   Phân tích ưu/nhược điểm của chương trình đã cài đặt, cách cải thiện.

---

## 3. Các quy định khác

* Bài tập được theo nhóm tối đa 5 sinh viên.
* Thời gian nộp được ghi trên trang môn học.
* Sinh viên sử dụng ngôn ngữ C/C++, Python hoặc Golang.

**Cấu trúc bài nộp:**

```
<MSSV1-MSSV2-MSSV3-MSSV4-MSSV5>.zip
 ├─ project_01_source
 │   └─ *.cpp / *.go / *.py
 └─ project_01_report
     └─ *.pdf
```

Trong đó:

* `<MSSV1-MSSV2-MSSV3-MSSV4-MSSV5>` là các mã số sinh viên của nhóm, sắp xếp theo thứ tự trong danh sách lớp.

* `.zip` là định dạng nén cho bài làm.

* `project_01_source` chứa mã nguồn.

* `project_01_report` chứa báo cáo PDF.

* Chương trình thực hiện yêu cầu nào không biên dịch được hoặc lỗi thì phần đó không có điểm.

* Cần lưu ý về phiên bản C++ để lựa chọn thư viện thích hợp; nếu dùng Python thì ghi rõ các package cần thiết vào file `requirements`.
