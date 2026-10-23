# Lotus Hotel AI.

Hệ thống quản lý khách sạn cho khách sạn vừa và nhỏ, xây dựng bằng FastAPI, Jinja2, Bootstrap 5, SQLAlchemy, SQLite/PostgreSQL/MySQL và Google Gemini. Hệ thống hỗ trợ 4 vai trò (`admin`, `receptionist`, `accountant`, `housekeeping`), quản lý phòng, khách hàng, đặt/nhận/trả/hủy phòng, dịch vụ, hóa đơn, thanh toán, báo cáo, trợ lý AI và chatbot nghiệp vụ nhiều lượt.

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


## Loại phòng và giá theo ngày (C05)

Admin mở **Loại phòng & bảng giá** (`/rates`) để sửa tên/tiện ích/sức chứa, giá thường, giá cuối tuần và trạng thái đang bán. Ngừng bán giữ lịch sử và booking đã xác nhận; chỉ xóa loại chưa có phòng hoặc bảng giá.

Giá đặc biệt áp dụng từ ngày bắt đầu đến trước ngày kết thúc, ưu tiên hơn giá cuối tuần (thứ Bảy/Chủ nhật), sau đó mới dùng giá thường. Hai khoảng giá đặc biệt đang áp dụng không được trùng nhau. Bỏ chọn Áp dụng để ngừng chương trình. Booking mới lưu chi tiết giá từng đêm; sửa giá/tên chương trình sau đó không đổi tiền đã chốt. Đặt mới tối đa 365 đêm và tổng tiền phòng trong giới hạn hóa đơn. Danh sách phòng hiển thị giá trung bình/đêm kèm tổng tiền; AI dùng giá thực tế từng đêm để kiểm tra ngân sách.

Chạy `python -m alembic upgrade head` để lên revision 0007 sau khi sao lưu DB. Booking legacy không được tự dựng giá đêm chưa từng lưu; xem docs/postgresql.md.


## Chi tiết đặt phòng (C06)

Nhấn mã đặt phòng từ Danh sách, Tổng quan hoặc Hóa đơn để mở `/bookings/{id}`. Trang hiển thị khách/liên hệ, ngày ở, giá đã chốt từng đêm, dịch vụ, dự tính hiện tại, hóa đơn và lịch sử trạng thái/người thao tác. Thời gian lịch sử hiển thị UTC. Mở trang không tự lập hoặc tính lại hóa đơn.

Các nút nhận/trả/hủy/ghi dịch vụ dành cho admin/lễ tân theo trạng thái; kế toán/admin có thể lập/cập nhật hóa đơn tạm và ghi nhận tiền đã thu. Lịch sử từng khoản thu chỉ hiện cho kế toán/admin, lễ tân xem tổng đã thu/còn thiếu. Backend vẫn kiểm tra quyền và trạng thái cho mọi thao tác. Hóa đơn tạm được phân biệt với dự tính đã có dịch vụ mới. Dữ liệu legacy thiếu giá đêm/lịch sử hoặc chênh số thu so với ledger có thông báo đối chiếu, không tự tạo lịch sử giả.


## Vận hành lưu trú (C07–C12)

- **Đổi lịch/gia hạn/đổi phòng:** tại chi tiết booking, nhập lý do, xem giá mới rồi xác nhận. Khách đang ở đổi phòng từ hôm nay Asia/Bangkok; các đêm đã ở giữ giá cũ, chặng phòng cũ được giữ và tạo việc dọn. Giá mới không được thấp hơn số đã thu trên hóa đơn. Dữ liệu legacy thiếu giá đêm phải đối chiếu trước khi đổi khi đang ở.
- **Lịch phòng `/calendar`:** 20 phòng/trang, tối đa 31 ngày; lọc ngày/loại/tầng/số khách. Nhấn mã để xem lịch sử, dấu + điền sẵn phòng/ngày. Khoảng lưu trú và bảo trì không gồm ngày kết thúc.
- **Buồng phòng `/housekeeping`:** pending → in_progress → inspection → ready. Admin/lễ tân phân công tài khoản housekeeping và kiểm tra cuối; nhân viên chỉ xem/thao tác việc của mình, không truy cập khách, tiền hoặc AI. Không thể dùng cập nhật trạng thái phòng để bỏ qua việc dọn chưa xong.
- **Bảo trì `/maintenance`:** tạo phiếu có người phụ trách và khoảng khóa bán; xung đột với booking/block hiện có bị từ chối. Đặt/sửa lịch, calendar và AI cùng dùng inventory theo chặng + block. Bảo trì theo ngày hết khoảng thì không chặn ngày sau; trạng thái physical maintenance thủ công vẫn cần xử lý riêng.
- **Bàn lễ tân `/frontdesk`:** khách đến/đi/đang ở, quá giờ trả, tiền còn phải thu; walk-in dùng tạo booking rồi nhận. Chỉ nhận phòng trong khoảng ngày đã đặt. No-show là trạng thái riêng, sau giờ cấu hình ngày đến; có hóa đơn phải xử lý tài chính trước. Nhận/trả thực tế được ghi thời gian UTC, ngưỡng nghiệp vụ theo Asia/Bangkok. Bảng hiển thị tối đa 200 booking hiệu lực cho dữ liệu demo.
- **Phụ thu:** admin cấu hình giờ và mức phí nhận sớm/trả muộn; mặc định phí 0. Mỗi loại là phí cố định một lần/lưu trú, không tính theo số giờ. Chỉ cộng sau xác nhận rõ của nhân viên, lưu người/thời điểm/mức đã chốt. Hóa đơn có cột phụ thu riêng.
- **Khách hàng:** tìm trên toàn CSDL/phân trang 20 khách; chi tiết tách đã ở/đang ở/chưa đến/hủy/no-show. Chỉ checked_out tính lượt đã lưu trú, đổi phòng không tăng lượt. Ngày hoàn tất dùng timestamp trả thực tế khi có, fallback ngày trả lịch cho legacy. Ghi chú sở thích chỉ cho admin/lễ tân, không gửi AI. Giấy tờ che mặc định, thao tác xem đầy đủ chỉ cho admin/lễ tân với response no-store. Khi sửa, để trống giữ giấy tờ cũ; chọn Xóa giấy tờ để gỡ rõ ràng.

API `/api/customers` trả `{items,total,page,pages,q}`; booking/invoice dùng schema đầu ra whitelist để tránh serialize quan hệ ORM có dữ liệu nhạy cảm. Migration mới nhất `0012`, chạy Alembic trước khi mở ứng dụng; sao lưu DB trước khi nâng. Migration backfill chặng phòng từ dữ liệu cũ biết được, không tự dựng các lần đổi phòng chưa từng được lưu. Các bước thu cọc/điều chỉnh/hoàn tiền và bàn giao ca vẫn nằm trong C13–C16, chưa coi đợt này là hoàn thiện toàn bộ hệ thống.

Nghiệm thu đợt C07–C12: PostgreSQL 117 test đạt; SQLite 115 đạt, 2 test riêng PostgreSQL bỏ qua. Test không gọi Gemini thật. Đã thử trình duyệt với database QA riêng: chọn ô lịch điền sẵn, preview/xác nhận đổi phòng, dọn/kiểm tra, lọc bàn lễ tân và vai trò buồng phòng. Kiểm tra responsive nhiều kích thước/thiết bị thực vẫn cần ở đợt UX cuối.
