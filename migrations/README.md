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

Development vẫn giữ `create_all` khi AUTO_CREATE_SCHEMA bật; nó không cập nhật các bảng đã tồn tại. Production tắt create_all/seed cũ và entrypoint `python -m scripts.start_server` chạy Alembic có khóa trước Uvicorn. Bản bàn giao ở revision 0022. Với database quản lý bằng Alembic, luôn nâng migration trước khi phục vụ HTTP.

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


## Tài chính và ca thu ngân — schema 0016

0013 tạo MoneyEntry làm sổ thu/hoàn duy nhất; Payment là mirror để tương thích API cũ, không cộng hai bảng. Migration chuyển Payment theo ngày thu đã biết; paid_amount còn thiếu thành legacy_opening, đánh dấu chưa rõ ngày thu. Tổng Payment lớn hơn paid_amount thì dừng nâng cấp để đối chiếu. 0015 thêm lý do hoàn, chính sách phí và bút toán điều chỉnh hủy/no-show. 0016 thêm ca thu ngân; giao dịch cũ giữ shift_id NULL vì không biết ca thực tế. Không có revision 0014 vì C14 chỉ đổi dịch vụ/giao diện.

Sau nâng cấp, mở ca trước khi thu/hoàn mới. Migration chặn downgrade khi schema cũ không giữ được lịch sử mới: không xóa dữ liệu để vượt chặn. Giữ dữ liệu phát sinh trước khi khôi phục backup. Đối chiếu bằng chứng từ thật, không dựng ca/ngày thu giả.
