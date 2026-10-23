# R02 · Phát hành Render

Đích được người dùng chọn: My Workspace, cter49132@gmail.com. Web khách sạn và PostgreSQL riêng tại Singapore, Free. Dịch vụ nhatot của dự án khác không thay đổi cấu hình.

PostgreSQL `lotus-hotel-db`, revision mục tiêu 0022, được tạo 23/10/2026. Hết hạn **22/11/2026 11:51 UTC**, sau buổi báo cáo dự kiến 30/10. Chuỗi kết nối nội bộ/mật khẩu được giữ trong environment và file local bị ignore, không có trong tài liệu.

Phát hành theo PR dev→main có merge commit, giữ feature commits/tác giả. CI gọi `python -m pytest` để giữ đúng đường import trên Linux, ghim action release SHA, Python 3.14.7 và Ubuntu 24.04. Lần CI đầu Docker build thành công nhưng pytest entrypoint không tìm thấy core.database; sửa tại R02, không bỏ test.

Trạng thái triển khai thực tế, URL, CI và kiểm tra qua redeploy sẽ được bổ sung ở phần nghiệm thu cuối sau khi Render trả trạng thái live. Không coi trigger/queued là triển khai thành công.
