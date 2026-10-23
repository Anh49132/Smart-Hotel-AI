# PostgreSQL và chuyển dữ liệu

`DATABASE_URL` chấp nhận `postgres://`, `postgresql://`, hoặc `postgresql+psycopg://`; ứng dụng dùng psycopg 3. Pool tối đa 5 kết nối/tiến trình. Host công khai mặc định yêu cầu TLS; URL có `sslmode` được giữ nguyên. Trên Render, dùng Internal URL trong cùng workspace/region; từ máy local dùng External URL với `sslmode=require`.

Cài dependency rồi chạy `python -m alembic upgrade head` trên database đích đã được xác nhận dành riêng cho khách sạn. Không dùng `create_all` để thay migration ở môi trường triển khai. Migration 0002 tái sử dụng enum PostgreSQL từ 0001; SQLite/MySQL vẫn dùng đường migration tương ứng.

## Chuyển từ SQLite

1. Dừng ghi vào nguồn và sao lưu. Không xóa hoặc đổi tên database đang dùng.
2. Chuẩn bị database/schema đích riêng, chạy migration đến head và bảo đảm chưa có dữ liệu nghiệp vụ. Không khởi động seed app trước khi nhập.
3. Đặt `TRANSFER_DATABASE_URL` trong môi trường bảo mật. Không đưa URL chứa mật khẩu vào Git, ảnh chụp hoặc log.
4. Chạy `python -m scripts.transfer_sqlite --source data/hotel.db`.
5. Công cụ đọc snapshot nhất quán, kiểm tra toàn vẹn nguồn, nhập trong transaction, kiểm tra số dòng/tổng Numeric và sửa sequence PostgreSQL. Đích có dữ liệu bị từ chối; không có chế độ ghi đè. Lỗi sẽ rollback dữ liệu nhập; giá trị sequence có thể tiến lên nếu lỗi cuối giao dịch nên lần thử lại sẽ đồng bộ lại sequence.
6. Sau khi đối chiếu và kiểm thử đăng nhập/đặt phòng/hóa đơn đạt mới đổi DATABASE_URL của ứng dụng. Giữ bản nguồn để đối chiếu.

Nếu nguồn thiếu bảng của migration mới, nâng cấp **bản sao nguồn** trước. Trường mới được dùng default của đích, không tự bịa lịch sử không tồn tại. Đây là công cụ chuyển sang đích rỗng; chuyển một hệ thống đang có dữ liệu ở cả hai bên cần quy trình khác.

## Kiểm thử PostgreSQL riêng

Đặt `HOTEL_TEST_DATABASE_URL` trỏ tới PostgreSQL dành cho kiểm thử rồi chạy `python -m pytest -q`. Test tự tạo schema tên ngẫu nhiên, chỉ drop schema do chính lượt test tạo. Không đặt biến này trỏ vào tài khoản có dữ liệu thật khi không cần thiết. Không đặt DATABASE_URL production để thay biến kiểm thử.

Test migration thực hiện upgrade/check/downgrade/upgrade trên schema tạm; test transfer kiểm tra ID, hash mật khẩu, tiền lẻ, từ chối đích có dữ liệu và sequence của lần insert tiếp theo.

## Giá của dữ liệu trước migration 0005

Booking mới lưu `booked_nightly_rate` ngay khi xác nhận. Booking cũ có hóa đơn dùng đơn giá trung bình từ tiền phòng đã ghi và đánh dấu `legacy_invoice`; hóa đơn đã checkout giữ nguyên tiền phòng thực tế để tránh lệch làm tròn. Booking cũ chưa có hóa đơn dùng giá niêm yết hiện tại và đánh dấu `legacy_current_rate`: hệ thống không thể dựng lại giá lịch sử đã không được lưu. Cần đối chiếu chứng từ trước khi bàn giao dữ liệu này.
