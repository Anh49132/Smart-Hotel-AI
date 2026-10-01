# Lotus Hotel AI.

Hệ thống quản lý khách sạn cho khách sạn vừa và nhỏ, xây dựng bằng FastAPI, Jinja2, Bootstrap 5, SQLAlchemy, MySQL và Ollama. Hệ thống hỗ trợ 3 vai trò (`admin`, `receptionist`, `accountant`), quản lý phòng, khách hàng, đặt/nhận/trả/hủy phòng, dịch vụ, hóa đơn, thanh toán, báo cáo, trợ lý AI và chatbot nghiệp vụ nhiều lượt.

## Cài đặt.

Yêu cầu Python 3.11+. Mặc định dùng SQLite; có thể cấu hình MySQL 8+. Các tính năng AI cần Ollama.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Mặc định database nằm tại `data/hotel.db`. Nếu dùng MySQL, tạo database rỗng và sửa `DATABASE_URL` theo ví dụ trong `.env.example`. Với database mới, chạy migration trước khi khởi động. Với database đã có bảng, xem `migrations/README.md` để đánh dấu baseline.

```bash
python -m alembic upgrade head
ollama pull qwen2.5
ollama serve
uvicorn main:app --reload
```

Mở `http://127.0.0.1:8000`. Lần chạy đầu tự tạo tài khoản quản trị demo `admin` / `Admin@123`; hãy đổi mật khẩu trước khi dùng ngoài môi trường học tập.

Trên Windows, có thể nhấp đúp `run-hotel.bat` để tự động dò Python, cài đặt, kiểm thử và mở ứng dụng. Nếu `.venv` được chép từ máy khác và không còn chạy được, launcher sẽ tạo `.venv-local` mới thay vì dùng đường dẫn Python cũ. Có thể đặt biến `HOTEL_PYTHON` nếu muốn chỉ định một `python.exe` cụ thể. Các màn hình quản trị Phòng, Đặt phòng, Khách hàng, Dịch vụ, Hóa đơn, Báo cáo, Trợ lý AI và Nhân sự đều thao tác trực tiếp với cơ sở dữ liệu.

## Kiểm thử

```bash
pytest -q
```

Các test bao phủ tạo đặt phòng, chống trùng lịch, trả phòng/tính hóa đơn, sinh email AI và chatbot với Ollama được mock. Logic overlap dùng điều kiện `new_check_in < old_check_out AND old_check_in < new_check_out` bên trong transaction có `SELECT ... FOR UPDATE` trên phòng để giảm race condition.

## API chính

- `/api/rooms`, `/api/room-types`, `/api/customers`, `/api/bookings`
- `/api/services`, `/api/service-usages`, `/api/invoices/{id}/payments`
- `/api/ai/room-advice`, `/api/ai/email`, `/api/ai/report`, `/api/ai/chat`

Swagger UI: `http://127.0.0.1:8000/docs`.

## An toàn AI

Prompt AI chỉ chứa danh sách phòng, trạng thái, giá, dịch vụ, thông tin đặt phòng không nhạy cảm hoặc số liệu tổng hợp. Chatbot không tự thay đổi dữ liệu và chỉ nhận tối đa 12 tin nhắn gần nhất trong phiên. Số giấy tờ, mật khẩu, token và chi tiết thanh toán cá nhân không được gửi cho Ollama. Khi Ollama timeout hoặc chưa chạy, API trả lỗi 503 rõ ràng và không tự bịa kết quả.


## Cấu trúc dự án

```text
backend/
  main.py          # Khởi tạo FastAPI, vòng đời ứng dụng
  dependencies.py  # Người dùng hiện tại và kiểm tra quyền
  api/             # Router JSON theo phòng, đặt phòng, khách, dịch vụ, hóa đơn, AI, nhân sự
  web/             # Router render HTML
  models/          # Model SQLAlchemy
  schemas/         # Dữ liệu đầu vào Pydantic
  services/        # Nghiệp vụ và truy vấn dữ liệu cho API/giao diện
frontend/
  templates/       # layouts, components, pages
  static/          # css, js, images
core/              # Cấu hình, kết nối database, mật khẩu và JWT
migrations/        # Alembic và lịch sử schema
data/             # SQLite local (không đưa database vào Git)
tests/             # backend, web, core; database tạm tự dọn sau test
main.py            # Điểm chạy: uvicorn main:app --reload
run-hotel.bat      # Launcher Windows
```

`core` không phụ thuộc `backend` hoặc `frontend`. Router kiểm tra quyền và gọi service; service thực hiện nghiệp vụ/truy vấn. Frontend chỉ chứa template và tài nguyên tĩnh. Model và schema hiện còn nhỏ nên được giữ trong `entities.py` và `inputs.py`, với export qua package để dễ chia nhỏ sau này.

Đường dẫn template, static, `.env` và SQLite được xác định theo thư mục dự án, không phụ thuộc thư mục làm việc của tiến trình. URL trang và API vẫn giữ nguyên; CSS nằm dưới `/static/css/`.

Sau khi cập nhật mã, chạy `python -m pip install -r requirements.txt`. Khi chuyển cấu trúc trên máy hiện tại, database gốc được giữ tại `data/hotel.before-restructure.db` để khôi phục; ứng dụng dùng `data/hotel.db`. Bản sao này không tự cập nhật theo dữ liệu mới.
