# Nhật ký AI và kiểm chứng

Các mục dưới đây ghi công việc thực tế trong phiên hỗ trợ, không dựng lại lịch sử trước đó.

## R01 — PostgreSQL

- Yêu cầu: thực hiện 5 commit đầu của kế hoạch, giữ nhánh `feature/...` và phân công hai email đã xác nhận.
- AI hỗ trợ: phân tích URL/driver, phát hiện enum `bookingstatus` bị tạo lại ở migration 0002 trên PostgreSQL, sinh công cụ chuyển từ snapshot SQLite vào đích rỗng, kiểm tra số dòng/tổng tiền và sequence.
- Quyết định kiểm soát: không đọc/in key, không dùng database dự án khác, không tự đổi DATABASE_URL local, không ghi đè đích có dữ liệu.
- Kiểm chứng: test URL, chuyển dữ liệu và migration; kết quả thực tế được ghi trong báo cáo hoàn thành sau mỗi phần.

## C01 — Toàn vẹn dữ liệu

- AI hỗ trợ bỏ ba bộ hàm bị định nghĩa trùng, kiểm tra tham chiếu ở service và ràng buộc miền dữ liệu ở DB.
- Điều chỉnh sau kiểm tra: SQLite cần tắt FK ngoài transaction trong thao tác batch migration, rồi kiểm tra toàn bộ FK trước commit; không chỉ bật PRAGMA ở ứng dụng.
- Kiểm chứng: PostgreSQL/SQLite, từ chối khách/loại phòng không tồn tại, chặn xóa lịch sử, ghi SQL trực tiếp sai ràng buộc và nâng DB SQLite có lịch sử/hóa đơn.
