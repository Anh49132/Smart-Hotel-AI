# Đóng gói và vận hành

Ứng dụng nội bộ cho nhân viên khách sạn, một tiến trình Uvicorn. Docker dùng Python 3.14.7 được ghim digest; requirements.lock ghim các thư viện đã kiểm thử. Render dùng PostgreSQL Singapore, không dùng SQLite trên ổ tạm.

## Chạy Docker

Tạo file môi trường riêng ngoài Git: APP_ENV=production, DATABASE_URL PostgreSQL có sẵn, SECRET_KEY ngẫu nhiên ít nhất 32 ký tự, BOOTSTRAP_ADMIN_PASSWORD riêng. Không dùng mật khẩu mẫu. Cài mới dùng `docker build -t lotus-hotel .` rồi `docker run --env-file <file-riêng> -p 8000:8000 lotus-hotel`. Migrations chạy trước khi nhận HTTP; lỗi migration dừng khởi động. Admin phải đổi mật khẩu lần đầu.

Demo bật DEMO_MODE=true, DEMO_SEED_ON_START=true và DEMO_STAFF_PASSWORD riêng từ 12 ký tự. Seed chỉ nhận CSDL chưa có phòng/đặt phòng và chỉ chạy một lần; không đặt lại tài khoản. Không bật seed trên dữ liệu đang vận hành.

## Render

Web Free, Docker, Singapore; branch main; auto-deploy tắt để kiểm tra CI trước khi phát hành. DATABASE_URL là URL nội bộ của CSDL riêng. API key Gemini chỉ đặt trong environment. PORT do Render cấp. FORWARDED_ALLOW_IPS=* chỉ đặt tại Render có proxy biên tin cậy để ứng dụng nhận đúng HTTPS; chạy trực tiếp giữ mặc định loopback. Health check `/healthz` thực hiện SELECT 1, trả 503 khi DB không sẵn sàng. Không có pre-deploy command trả phí: entrypoint chạy Alembic có khóa advisory trước Uvicorn.

Web Free có thể ngủ khi không có truy cập; mở trước buổi demo và kiểm tra lại đăng nhập, AI, PDF. Hạn mức web dùng chung workspace; không thay đổi dịch vụ nhatot. PostgreSQL Free tạo 23/10/2026, hết hạn 22/11/2026; báo cáo dự kiến 30/10/2026. Đối chiếu hạn trong Dashboard trước buổi báo cáo. Không bật dịch vụ trả phí tự động.

## Sao lưu và khôi phục

Cài PostgreSQL client tương thích (ở Windows đặt PG_BIN tới thư mục bin). Cung cấp BACKUP_DATABASE_URL bằng môi trường riêng, chạy `python -m scripts.postgres_backup backup data/backups/hotel-<ngay>.dump`. Dump custom lấy cùng snapshot với manifest; manifest chứa số dòng, tổng hóa đơn/sổ tiền, sequence, revision và SHA-256. Bảo vệ cả dump lẫn manifest như dữ liệu khách hàng. Không đẩy lên Git.

Chuẩn bị một database mới, không có bảng, đặt RESTORE_DATABASE_URL riêng rồi chạy `python -m scripts.postgres_backup restore <archive.dump> --confirm-empty-target`. Công cụ từ chối đích có bảng; restore trong một transaction, không có --clean; so sánh lại manifest sau restore. Chỉ khôi phục archive tin cậy. Không truyền mật khẩu trên command line. Dừng ghi trong cửa sổ bảo trì khi cần kiểm tra sequence nhất quán tuyệt đối; snapshot dữ liệu không đóng băng các sequence ngoài transaction.

CSDL Render hiện chặn kết nối ngoài; chạy export từ máy có quyền mạng phù hợp hoặc công cụ Render hỗ trợ. Nếu cần mở IP quản trị, chỉ cho IP tin cậy trong thời gian bảo trì và đóng lại sau đó; không mở toàn Internet. Free không thay cho chính sách backup tự động. Xuất bản sao trước hạn và thử restore trước khi xóa/chuyển đích.

## Chuyển sang Neon và quay lại bản mã

Chỉ chuyển khi đã chọn đích: tạo PostgreSQL đích, đóng ghi nguồn, backup/restore và đối chiếu, cấu hình DATABASE_URL mới qua môi trường, triển khai rồi thử luồng đặt/thu/hoàn tiền. Giữ nguồn nguyên trạng trong thời gian xác nhận. Không chạy seed vào dữ liệu chuyển.

Rollback code chỉ dùng bản tương thích revision hiện tại. Bản trước migration 0019/0022 không tự hiểu revision mới khi chạy entrypoint; không bấm rollback về bản đó một cách mù quáng. Dùng artifact phát hành đã hỗ trợ 0022 hoặc restore bản sao vào DB mới với phiên bản ứng dụng tương ứng. Database rollback là quy trình riêng và có nguy cơ mất giao dịch sau thời điểm sao lưu.

Giới hạn: một worker, giới hạn AI trong bộ nhớ từng tiến trình, body tối đa 64 KB, chưa có HA/SLA/kiểm thử tải song song lớn. CI kiểm tra SQLite/PostgreSQL và build Docker; kết quả thực tế được ghi riêng, không coi file workflow là bằng chứng CI đã xanh.
