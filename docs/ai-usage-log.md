# Nhật ký AI và kiểm chứng

Các mục dưới đây ghi công việc thực tế trong phiên hỗ trợ, không dựng lại lịch sử trước đó.

## R01 — PostgreSQL

- Yêu cầu: thực hiện 5 commit đầu của kế hoạch, giữ nhánh `feature/...` và phân công hai email đã xác nhận.
- AI hỗ trợ: phân tích URL/driver, phát hiện enum `bookingstatus` bị tạo lại ở migration 0002 trên PostgreSQL, sinh công cụ chuyển từ snapshot SQLite vào đích rỗng, kiểm tra số dòng/tổng tiền và sequence.
- Quyết định kiểm soát: không đọc/in key, không dùng database dự án khác, không tự đổi DATABASE_URL local, không ghi đè đích có dữ liệu.
- Kiểm chứng: test URL, chuyển dữ liệu và migration; kết quả thực tế được ghi trong báo cáo hoàn thành sau mỗi phần.
