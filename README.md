# Lotus Hotel AI.

Hệ thống quản lý khách sạn cho khách sạn vừa và nhỏ, xây dựng bằng FastAPI, Jinja2, Bootstrap 5, SQLAlchemy, SQLite/PostgreSQL/MySQL và Google Gemini. Hệ thống hỗ trợ 3 vai trò (`admin`, `receptionist`, `accountant`), quản lý phòng, khách hàng, đặt/nhận/trả/hủy phòng, dịch vụ, hóa đơn, thanh toán, báo cáo, trợ lý AI và chatbot nghiệp vụ nhiều lượt.

## Cài đặt.

Yêu cầu Python 3.11+. Mặc định dùng SQLite; có thể cấu hình PostgreSQL (đích triển khai) hoặc MySQL 8+. Các tính năng AI cần Internet và API key Gemini trên backend.

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Điền `GEMINI_API_KEY` trong `.env` trước khi dùng AI. Giữ key trong `.env` hoặc biến môi trường của máy chủ; không đưa vào frontend, Git hay nội dung chat. Nếu đã có `.env`, thêm các biến Gemini bên dưới và giữ cấu hình database hiện có. Không cần cài hoặc chạy Ollama.

```dotenv
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.5-flash-lite
GEMINI_TIMEOUT_SECONDS=60
GEMINI_MAX_OUTPUT_TOKENS=2048
```

Model mặc định là `gemini-3.5-flash-lite`; có thể đổi `GEMINI_MODEL` sang model Gemini mà tài khoản được phép sử dụng theo [danh sách model của Google](https://ai.google.dev/gemini-api/docs/models). Hệ thống gọi [Gemini REST API](https://ai.google.dev/api/generate-content) bằng `httpx` đã có trong dependencies, truyền key qua header `x-goog-api-key`. Có thể dùng `GOOGLE_API_KEY` nếu không đặt `GEMINI_API_KEY`. Khi đổi cấu hình, khởi động lại ứng dụng.

Mặc định database nằm tại `data/hotel.db`. Nếu dùng MySQL, tạo database rỗng và sửa `DATABASE_URL` theo ví dụ trong `.env.example`. Với database mới, chạy migration trước khi khởi động. Với database đã có bảng, xem `migrations/README.md` để đánh dấu baseline.

```bash
python -m alembic upgrade head
uvicorn main:app --reload
```

Mở `http://127.0.0.1:8000`. Lần chạy đầu tự tạo tài khoản quản trị demo `admin` / `Admin@123`; hãy đổi mật khẩu trước khi dùng ngoài môi trường học tập.

Trên Windows, có thể nhấp đúp `run-hotel.bat` để tự động dò Python, cài đặt, kiểm thử và mở ứng dụng. Nếu `.venv` được chép từ máy khác và không còn chạy được, launcher sẽ tạo `.venv-local` mới thay vì dùng đường dẫn Python cũ. Có thể đặt biến `HOTEL_PYTHON` nếu muốn chỉ định một `python.exe` cụ thể. Các màn hình quản trị Phòng, Đặt phòng, Khách hàng, Dịch vụ, Hóa đơn, Báo cáo, Trợ lý AI và Nhân sự đều thao tác trực tiếp với cơ sở dữ liệu.

## Kiểm thử

```bash
pytest -q
```

Các test bao phủ tạo đặt phòng, chống trùng lịch, trả phòng/tính hóa đơn, sinh email AI và chatbot với Gemini được mock. Test transport kiểm tra payload một/nhiều lượt, parse kết quả, khóa chỉ nằm ở header, lọc dữ liệu nhạy cảm và lỗi thiếu key/quota/timeout/phản hồi không hợp lệ. Test không gọi Gemini thật hoặc tiêu thụ quota. Logic overlap dùng điều kiện `new_check_in < old_check_out AND old_check_in < new_check_out`; `SELECT ... FOR UPDATE` chỉ có tác dụng trên database hỗ trợ khóa hàng, SQLite dùng khóa ghi trước khi kiểm tra phòng trống. Bộ test chạy hai session đồng thời cho cả SQLite và PostgreSQL.

Revision `0002` thêm lịch sử trạng thái đặt phòng, từng khoản thanh toán và bản nháp kết quả AI. Trước khi nâng cấp database cũ, xem [hướng dẫn migration](migrations/README.md) để sao lưu và khôi phục. API `/api/bookings/{id}/history` và `/api/invoices/{id}/payments` cho phép xem lịch sử; trang Trợ lý AI có danh sách duyệt kết quả cho quản trị viên/kế toán. Bản nháp AI vẫn cần người dùng kiểm tra trước khi sử dụng. Dữ liệu phát sinh trước revision `0002` không có lịch sử chi tiết để truy hồi.

## API chính

- `/api/rooms`, `/api/room-types`, `/api/customers`, `/api/bookings`
- `/api/services`, `/api/service-usages`, `/api/invoices/{id}/payments`
- `/api/ai/room-advice`, `/api/ai/email`, `/api/ai/report`, `/api/ai/chat`

Swagger UI: `http://127.0.0.1:8000/docs`.

## An toàn AI

Prompt nghiệp vụ lấy danh sách phòng, giá, dịch vụ, tên khách/thông tin lịch đặt phòng cần cho email hoặc số liệu tổng hợp; không lấy số giấy tờ, số điện thoại/email khách, ghi chú đặt phòng hay chi tiết tài khoản/thẻ từ database. Nội dung được gửi tới dịch vụ Google Gemini, không còn xử lý bằng model local.

Chatbot không tự thay đổi dữ liệu và chỉ nhận tối đa 12 tin nhắn gần nhất trong phiên. Bộ lọc che các mẫu số giấy tờ/thẻ, hộ chiếu, mật khẩu/token gắn nhãn và khóa cấu hình trong văn bản tự do trước khi gọi Gemini. Bộ lọc theo mẫu không nhận diện được mọi cách viết dữ liệu nhạy cảm: nhân viên không nhập giấy tờ, mật khẩu hoặc thông tin thanh toán cá nhân vào chat/tiện ích. Giá phòng và số liệu tổng hợp giữ dạng số, không dùng bộ lọc số giấy tờ cho số liệu thống kê.

Thiếu key, key không hợp lệ, model không truy cập được, quota hoặc timeout sẽ trả lỗi 503 rõ ràng; nội dung bị chặn trả 422, phản hồi rỗng/sai cấu trúc/chưa hoàn chỉnh trả 502. Không trả lỗi thô của nhà cung cấp hay tự động gửi lại yêu cầu để tránh lộ dữ liệu và tiêu thụ quota lặp. Bản nháp AI cần được kiểm tra trước khi dùng.


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


## Tài khoản và cấu hình production

Hệ thống phục vụ nhân sự nội bộ. Admin tạo tài khoản tại Nhân sự & quyền; nhân sự phải đổi mật khẩu tạm tại Tài khoản trước khi thao tác. Không mở đăng ký công khai cho khách lưu trú. Admin có thể đổi vai trò, khóa/mở khóa và đặt lại mật khẩu người khác; không tự khóa hoặc tự đổi vai trò. Đổi/reset mật khẩu, đổi quyền, khóa/mở khóa làm mất hiệu lực các JWT cũ. Đổi mật khẩu cá nhân cấp phiên mới cho trình duyệt đang sử dụng.

Khi triển khai HTTPS, đặt `APP_ENV=production`, `SECRET_KEY` ngẫu nhiên ít nhất 32 ký tự và chạy `python -m alembic upgrade head` trước khi khởi động. Production tắt tự tạo schema và seed demo, dùng cookie Secure/HttpOnly/SameSite=Lax. Database trống cần `BOOTSTRAP_ADMIN_PASSWORD` riêng (từ 8 ký tự, tối đa 72 byte UTF-8); sau tạo tài khoản có thể gỡ biến bootstrap. Production từ chối khởi động nếu có tài khoản hoạt động còn mật khẩu mẫu `Admin@123`. Với DB cũ, đổi mật khẩu trong môi trường local trước khi chuyển dữ liệu.

Đăng nhập giới hạn 5 lần/tài khoản và 30 lần/IP trong cửa sổ 5 phút. Bộ đếm có giới hạn bộ nhớ và nằm trong một tiến trình: chạy một worker cho demo; nếu tăng worker/instance phải dùng kho đếm chung. Cookie API chặn nội dung form và Origin khác máy chủ; client nghiệp vụ gửi JSON cùng nguồn. Chính sách nghiệp vụ vẫn được kiểm tra ở backend.

## Nhánh phát triển

Git Flow: `main → dev → feature/...`. Tách feature từ dev, kiểm thử rồi nhập lại dev; nghiệm thu đợt rồi PR dev → main để phát hành. Render theo main. Xem [kế hoạch và phân công](docs/ke-hoach-hoan-thien-2-nguoi.md). Các merge local không thay thế review thực tế bằng tài khoản GitHub của người còn lại.
