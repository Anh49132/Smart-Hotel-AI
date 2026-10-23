# R02 · Phát hành Render

Đích được người dùng chọn: My Workspace, cter49132@gmail.com. Web khách sạn và PostgreSQL riêng tại Singapore, Free. Dịch vụ nhatot của dự án khác không thay đổi cấu hình.

PostgreSQL `lotus-hotel-db`, revision mục tiêu 0022, được tạo 23/10/2026. Hết hạn **22/11/2026 11:51 UTC**, sau buổi báo cáo dự kiến 30/10. Chuỗi kết nối nội bộ/mật khẩu được giữ trong environment và file local bị ignore, không có trong tài liệu.

Phát hành theo PR dev→main có merge commit, giữ feature commits/tác giả. CI gọi `python -m pytest` để giữ đúng đường import trên Linux, ghim action release SHA, Python 3.14.7 và Ubuntu 24.04. Lần CI đầu Docker build thành công nhưng pytest entrypoint không tìm thấy core.database; sửa tại R02, không bỏ test.

## Nghiệm thu cloud

- URL: **https://lotus-hotel-ai.onrender.com**; service `srv-dbdlo28ae00c738kprgg`, Free/Docker/Singapore, main, auto-deploy tắt, health `/healthz`.
- PR #1 dev→main đã merge sau CI xanh: https://github.com/Anh49132/Smart-Hotel-AI/pull/1. Run dev: https://github.com/Anh49132/Smart-Hotel-AI/actions/runs/39958052673 và run PR https://github.com/Anh49132/Smart-Hotel-AI/actions/runs/39958059479 đều success (PostgreSQL, SQLite, Docker).
- Artifact đầu `b22e0cca5fffb8e9a74f90bd2bf6a78d31aba45a`, deploy `dep-dbdlo30ae00c738kpt70` đã **live** lúc 13:09 UTC 23/10/2026. Migration trước startup, seed giả 12 phòng/21 booking. Admin bootstrap được đổi mật khẩu qua API của chính app; file quyền riêng chỉ ở máy local, không có trong Git/chat.
- Smoke thật đạt 18 mục: health, đăng nhập và Secure/HttpOnly cookie, 9 trang, số phòng/booking, API chưa đăng nhập bị từ chối, PDF, Origin khác bị chặn và một request Gemini báo cáo từ số tổng hợp. Chi tiết `render-smoke-evidence.json`. Không thay test luồng tài chính bằng smoke này.
- API/Browser QA chỉ dùng dữ liệu giả. Có thêm dịch vụ `QA-PERSIST-20261023` để phân biệt dữ liệu được giữ thật với seed tạo lại. Fingerprint phòng/booking/dịch vụ/bản nháp AI được so sánh qua redeploy, bằng chứng chốt trong `render-persistence-evidence.json`.
- Redeploy `dep-dbdoctqvcj2c738fbpjg` cùng artifact đã **live** 16:09 UTC 23/10/2026. Fingerprint trước/sau khớp, mật khẩu mới vẫn đăng nhập vào tổng quan, seed không reset. Đây là kiểm chứng khởi động lại artifact tương thích revision 0022; không tuyên bố đã rollback qua Dashboard về bản mã không tương thích schema. Ảnh online sau redeploy: `images/render-live-dashboard.png`.
- Dịch vụ `nhatot` được đọc đối chiếu: cùng repo/branch/free/autoDeploy off và updatedAt 22/10/2026 18:10 UTC như trước, không có thay đổi cấu hình từ đợt này.

File `data/demo-access.local.json` trên máy người triển khai chứa URL/tài khoản demo riêng; không chứa API key hoặc DB URL, bị Git ignore và giới hạn ACL. Nhân viên demo phải đổi mật khẩu tạm lần đầu. Không đăng mật khẩu lên README. Free DB hết hạn như trên, cần backup/chuyển trước hạn; credential file local không thay bản backup.
