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
