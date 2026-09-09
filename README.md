# Lotus Hotel AI

Hệ thống quản lý khách sạn cho khách sạn vừa và nhỏ, xây dựng bằng FastAPI, Jinja2, Bootstrap 5, SQLAlchemy, MySQL và Ollama. Hệ thống hỗ trợ 3 vai trò (`admin`, `receptionist`, `accountant`), quản lý phòng, khách hàng, đặt/nhận/trả/hủy phòng, dịch vụ, hóa đơn, thanh toán, báo cáo, trợ lý AI và chatbot nghiệp vụ nhiều lượt.

## Cài đặt

Yêu cầu Python 3.11+, MySQL 8+ và Ollama.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Tạo CSDL bằng `migrations/001_initial.sql`, sau đó sửa `DATABASE_URL` trong `.env` cho đúng tài khoản MySQL.

```bash
mysql -u root -p < migrations/001_initial.sql
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

