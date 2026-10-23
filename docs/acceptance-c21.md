# Nghiệm thu tích hợp C21 — 23/10/2026

## Phạm vi đã chạy

- PostgreSQL 16 local, schema ngẫu nhiên tách biệt: **157 test đạt**.
- SQLite trong thư mục tạm: **155 đạt, 2 bỏ qua** (hai test chỉ áp dụng PostgreSQL).
- AI trong bộ test dùng mock. Bốn request Gemini thật bằng dữ liệu giả được lưu riêng trong `ai-live-evaluation-2026-10-23.json`, có ghi cả lỗi bộ lọc mã booking đã phát hiện và sửa.
- Python trên máy nghiệm thu: 3.14.7. Có cảnh báo deprecation từ thư viện; không dùng kết quả này để khẳng định mọi phiên bản Python đều đã thử.

Luồng `tests/backend/test_release_acceptance.py`: lễ tân mở ca, AI tư vấn, đặt/thu cọc có retry, nhận phòng, dịch vụ, chuyển phòng giữa kỳ và gia hạn, checkout; kế toán mở ca/thu đủ, đối chiếu folio và báo cáo, chốt ca; nhân viên buồng phòng dọn, lễ tân kiểm tra lại. Tiền phòng 3 đêm 2.700.000 + dịch vụ 100.000 = 2.800.000; cọc 500.000 + thu cuối 2.300.000 = 2.800.000; số dư 0. Test dùng clock nghiệp vụ cố định cho ledger/hóa đơn, không sửa timestamp dữ liệu thật.

Các bộ hồi quy riêng kiểm tra đặt trùng/giao nhau/sát biên, đổi phòng rollback, hai lần thu/hoàn đồng thời, giữ phí sau hủy, chốt ca cùng lúc thu, quyền từng vai trò, token thu hồi, đầu vào tham chiếu và migration nâng/hạ/nâng trên SQLite/PostgreSQL. Các phòng/giá từ API được tạo thành Option bằng text thay vì nối HTML nhằm tránh diễn giải dữ liệu quản trị thành mã giao diện.

## Số đo demo

`python -m scripts.benchmark_demo --postgres --output docs/benchmark-postgres-2026-10-23.json` tạo schema riêng với 30 phòng/120 booking rồi tự dọn. 6 màn hình × 12 GET = 72 request, tất cả HTTP 200. Median từng màn 6,75–29,30 ms; mẫu chậm nhất 68,21 ms. Đây là TestClient local, một tiến trình, tuần tự, không Internet/AI; không phải benchmark tải đồng thời hoặc thời gian cold start Render. Với 12 mẫu, p95 lấy mẫu lớn nhất; không coi là SLA.

## Phần cần thử tiếp

C22 kiểm tra trình duyệt, responsive và bản in; C23 kiểm tra dump/restore thực tế và đóng gói; R02 nghiệm thu URL HTTPS, dữ liệu bền sau redeploy và một lượt AI online. Không dùng số test để thay cho review chéo của hai thành viên hoặc xác nhận đủ toàn bộ tiêu chí học phần.
