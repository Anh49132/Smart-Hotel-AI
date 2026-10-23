# Migration cơ sở dữ liệu

Cấu hình dùng chung `DATABASE_URL` trong `.env`; đường dẫn SQLite tương đối được tính từ thư mục gốc dự án.

## Database mới

Tạo database rỗng trước nếu dùng MySQL, sau đó chạy từ thư mục gốc:

```bash
python -m alembic upgrade head
```

## Database đã có dữ liệu trước khi tách cấu trúc

Revision `0001` mô tả schema hiện có, không thay đổi schema nghiệp vụ. Sao lưu database, đối chiếu schema với revision trước khi đánh dấu baseline:

```bash
python -m alembic stamp 0001
python -m alembic check
```

`stamp` chỉ ghi phiên bản, không tạo bảng hay sửa dữ liệu. Không chạy migration tạo bảng ban đầu trên database đã có bảng. Nếu `check` báo khác biệt, cần xử lý khác biệt đó trước khi tạo migration tiếp theo.

## Các lần thay đổi model tiếp theo

```bash
python -m alembic revision --autogenerate -m "describe schema change"
# Đọc và kiểm tra file sinh ra trong migrations/versions trước khi áp dụng.
python -m alembic upgrade head
```

Ứng dụng vẫn giữ `create_all` lúc khởi động để tương thích cách chạy demo cũ; nó không cập nhật các bảng đã tồn tại. Với database quản lý bằng Alembic, chạy migration trước khi khởi động ứng dụng.

## Nâng cấp lên revision 0002

Revision `0002` bổ sung `booking_status_history`, `payments` và `ai_results`. Với database đã ở `0001`, sao lưu trước rồi chạy `python -m alembic upgrade head`. Những thanh toán và chuyển trạng thái phát sinh trước `0002` chỉ còn số tổng hợp/trạng thái hiện tại; migration không thể dựng lại đầy đủ lịch sử cũ.

Với SQLite đang chạy, dừng ứng dụng trước khi sao lưu hoặc khôi phục. Có thể dùng Python để tạo bản sao nhất quán:

```python
import sqlite3
source = sqlite3.connect("data/hotel.db")
backup = sqlite3.connect("data/hotel.backup.db")
source.backup(backup)
backup.close()
source.close()
```

Để khôi phục, sao chép `data/hotel.backup.db` thành `data/hotel.db` khi ứng dụng đã dừng; giữ riêng bản hiện tại nếu cần đối chiếu. Chạy `python -m alembic current` để kiểm tra phiên bản sau khôi phục. Với MySQL, dùng công cụ sao lưu/khôi phục của MySQL và tài khoản có quyền phù hợp.
