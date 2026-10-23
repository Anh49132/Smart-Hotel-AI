# Lotus Hotel AI · AIA331

Hệ thống quản lý nội bộ khách sạn vừa và nhỏ, tích hợp Google Gemini. FastAPI, Jinja2/Bootstrap, SQLAlchemy/Alembic và PostgreSQL; SQLite để phát triển local. Bản Docker dùng Python 3.14.7 với dependency lock.

**Demo:** https://lotus-hotel-ai.onrender.com · [CI](https://github.com/Anh49132/Smart-Hotel-AI/actions) · [Báo cáo kỹ thuật](docs/technical-report.md).

## Chức năng

- Admin, lễ tân, kế toán và buồng phòng; quản trị tạo/kích hoạt tài khoản, phân quyền và reset mật khẩu; đổi mật khẩu lần đầu và thu hồi phiên cũ.
- Loại phòng/phòng/bảng giá, lịch phòng, tìm phòng theo ngày/khách/loại, bảo trì có khoảng ngày.
- Khách/lịch sử lưu trú, đặt/nhận/trả/hủy/no-show, đổi lịch/phòng có lịch sử và giá từng đêm.
- Dịch vụ, phụ thu/giảm giá, cọc/thu/hoàn, sổ tiền, bảng kê và chứng từ PDF tiếng Việt; đối soát theo từng booking.
- Công suất theo lịch, hóa đơn, thu/hoàn/công nợ theo mốc được công bố; xuất CSV.
- Gemini tư vấn phòng có đối chiếu, email theo ngữ cảnh, báo cáo/khuyến mại; bản nháp lưu model/prompt/source và lịch sử duyệt.

Phạm vi một khách sạn, không có cổng khách tự đặt/thanh toán hoặc đăng ký công khai. Thanh toán là nhân viên ghi nhận thực tế, chứng từ nội bộ không thay hóa đơn điện tử. Email AI là bản nháp, chưa gửi tự động.

## Chạy local

Khuyến nghị Python **3.14.7** như bản đã kiểm thử. Tạo môi trường và cài đặt:

```powershell
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.lock
Copy-Item .env.example .env
.venv/Scripts/python.exe -m alembic upgrade head
.venv/Scripts/python.exe -m uvicorn main:app --reload
```

Mở http://127.0.0.1:8000. .env chứa DATABASE_URL, GEMINI_API_KEY và GEMINI_MODEL. Giữ cấu hình đang dùng nếu đã có .env, không chép đè. Key chỉ ở backend, không commit hoặc gửi trong chat. Model mặc định gemini-3.5-flash-lite đã gọi thử bằng key được cấu hình; tài khoản cần quyền truy cập/quota model.

Development mặc định tạo admin/Admin@123 chỉ cho local và buộc đổi lần đầu. Production yêu cầu SECRET_KEY ngẫu nhiên ít nhất 32 ký tự, BOOTSTRAP_ADMIN_PASSWORD riêng và PostgreSQL. Không dùng mật khẩu mẫu trên Internet. `python -m scripts.start_server` chạy migration có khóa trước khi phục vụ; production không tự create_all.

Demo đầy đủ chỉ dành CSDL mới riêng: DEMO_MODE=true, DEMO_SEED_ON_START=true, DEMO_STAFF_PASSWORD riêng từ 12 ký tự. Seed tạo 12 phòng/21 booking giả, nhân sự và mẫu tài chính một lần; chạy lại không reset dữ liệu/mật khẩu. Không bật seed trên khách sạn đang có dữ liệu. Xem [dữ liệu demo/UX](docs/demo-data-and-ux.md).

Windows có thể dùng run-hotel.bat; kiểm tra môi trường trước khi dùng dữ liệu hiện tại. Database local, .env, backup và file *.local.json không được đưa vào Git.

## Kiểm thử

```powershell
.venv/Scripts/python.exe -m pytest -q --disable-warnings
# PostgreSQL QA riêng; điền URL riêng bằng môi trường, không đặt vào Git:
# HOTEL_TEST_DATABASE_URL=<URL-QA>
.venv/Scripts/python.exe -m pytest -q --disable-warnings
```

Test tạo DB/schema tạm; không dùng tài khoản DB production làm đích kiểm thử. Kết quả phát hành local: PostgreSQL **164 passed**, SQLite **162 passed, 2 skipped**. Unit/integration AI dùng mock; bốn request Gemini thật bằng dữ liệu giả được ghi riêng. Có cảnh báo deprecation. [Nghiệm thu](docs/release-evidence.md) và [ma trận yêu cầu/test](docs/traceability.md) ghi phạm vi và giới hạn. GitHub Actions chạy cả hai DB và Docker build; xem run thực tế thay vì suy từ file workflow.

Backend kiểm tra overlap `[check_in, check_out)`, khóa và transaction khi đặt/đổi/thu/hoàn; request tiền chống xử lý lặp. Giá chụp theo đêm, MoneyEntry là sổ chuẩn. Báo cáo tách hóa đơn, dòng tiền, hoàn và công nợ hiện tại; dữ liệu thu cũ thiếu ngày giữ legacy, không dựng lịch sử.

## AI và dữ liệu riêng tư

Gemini REST API qua httpx, key ở header. Tư vấn chỉ dùng phòng backend lọc và kiểm chứng; model không được quyết định giá hoặc ghi giao dịch. Báo cáo đối chiếu schema và snapshot. Email tự do vẫn cần người kiểm tra/duyệt. Không gửi giấy tờ hoặc thông tin thanh toán; không nhập bí mật vào chat. Bộ lọc mẫu không nhận biết mọi cách viết dữ liệu nhạy cảm.

Giới hạn một tiến trình: 10 request AI/phút/người, tối đa hai đang xử lý, timeout có thông báo, context hữu hạn. Không tự retry nghiệp vụ khi lỗi mạng. [Nhật ký AI SDLC](docs/ai-usage-log.md), [đánh giá gọi thật](docs/ai-live-evaluation-2026-10-23.json).

## Triển khai, backup và bàn giao

[Docker/Render/backup/restore](docs/deployment.md) · [R02 thực tế](docs/render-release.md) · [PostgreSQL/transfer](docs/postgresql.md) · [migration](migrations/README.md).

Web và PostgreSQL Render Free riêng tại Singapore. DB tạo 23/10/2026, **hết hạn 22/11/2026**; báo cáo dự kiến 30/10. Web có thể ngủ/cold start và dùng quota chung workspace. Mở trước buổi báo cáo, kiểm tra AI và chuẩn bị local dự phòng. Cần backup/chuyển DB trước hạn, không coi Free là sao lưu tự động hoặc SLA.

`python -m scripts.postgres_backup backup <archive.dump>` đọc BACKUP_DATABASE_URL; restore vào **database mới không có bảng** bằng RESTORE_DATABASE_URL và `restore <archive.dump> --confirm-empty-target`. Archive/manifest chứa dữ liệu riêng, phải bảo vệ. Công cụ kiểm tra checksum/số dòng/tổng tiền/sequence/revision, không ghi đè đích đang có bảng. [Bằng chứng restore QA](docs/backup-restore-evidence.json).

## Tài liệu bảo vệ

[Báo cáo](docs/technical-report.md) · [Từ điển dữ liệu](docs/data-dictionary.md) · [Kịch bản demo và câu hỏi](docs/demo-script.md) · [Slide PowerPoint](output/presentation/lotus-hotel-aia331-no-shifts.pptx) · [Kế hoạch/phân công Git](docs/ke-hoach-hoan-thien-2-nguoi.md).

Git Flow dùng main/dev/feature. Coding agent hỗ trợ theo phân công hai tài khoản; author commit không tự chứng minh review chéo hay diễn tập của sinh viên. Hai thành viên cần tự review, hiểu code và tập trình bày thật. Tài liệu đánh giá đầu vào được giữ riêng để đối chiếu lịch sử, không phải kết luận bản cuối.

## Cấu trúc

backend/api và backend/web: HTTP; backend/services: nghiệp vụ; backend/models và schemas: dữ liệu/ràng buộc; core: cấu hình/bảo mật/DB/giới hạn; frontend: template và tài nguyên local; migrations: Alembic; scripts: seed/start/backup/transfer; tests: backend/web/core; docs và output: minh chứng, báo cáo, PDF giả và slide.
