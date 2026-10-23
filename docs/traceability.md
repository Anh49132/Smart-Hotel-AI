# Ma trận yêu cầu – minh chứng

| Yêu cầu | Triển khai | Test chính |
|---|---|---|
| Đăng nhập/phân quyền/tạo tài khoản nhân viên bởi admin | core/security, users API | test_staff_security.py, test_finance_access.py |
| Loại phòng/phòng/giá/trạng thái | room/rate services, housekeeping | test_room_rates.py, test_housekeeping.py |
| Khách/lịch sử | guest history API/web | test_guest_history.py |
| Đặt/nhận/trả/hủy | booking/frontdesk services | test_business.py, test_booking_consistency.py, test_frontdesk.py |
| Phòng trống ngày/khách/loại | availability/calendar/block | test_room_calendar.py, test_maintenance.py, test_booking_changes.py |
| Dịch vụ/hóa đơn | invoice/folio | test_invoice_correctness.py, test_folios.py |
| Cọc/thu/hoàn trực tiếp | money/refund | test_deposits.py, test_refunds.py, test_payments_without_shifts.py |
| Công suất/doanh thu/đặt theo thời gian | operating reports, CSV | test_operating_reports.py |
| Tư vấn phòng AI | room advice + Gemini | test_room_advice.py, test_gemini.py |
| Email AI | email service, review history | test_email_history.py, test_gemini.py |
| Báo cáo/khuyến mại AI | ai_reports + ai limiter | test_ai_reports.py |
| CSDL/ràng buộc/migration/transfer | models, Alembic, scripts | test_integrity.py; tests/core/test_migrations.py, test_transfer.py, test_legacy_money.py |
| Toàn luồng/đồng thời/quyền | backend + transaction | test_release_acceptance.py, test_operational_integration.py và concurrency trong các test tài chính/booking |
| Seed/UX/PDF | demo service, page service, PDF | test_demo_seed.py; tests/web; docs/images; output/pdf |
| Health/body/production | backend/main, startup, body limit | test_deployment.py |
| Backup/restore | scripts/postgres_backup.py | scripts/verify_backup_restore.py; backup-restore-evidence.json |

Test backend nằm trong tests/backend, các đường khác đã ghi riêng. Danh sách tên hàm và kết quả được truy xuất bằng `pytest --collect-only`/`pytest -q`, không coi tên file là bảo chứng mọi trường hợp.

| Tiêu chí chấm | Bằng chứng và giới hạn |
|---|---|
| 1 Chức năng | C01–C20; acceptance đa vai trò |
| 2 Kiến trúc | services/models/core/API/web; cần review chéo người thật |
| 3 CSDL | migration 0022, constraints, seed, dump/restore có đối chiếu |
| 4 Giao diện | browser desktop/mobile, loading/lỗi/pagination, PDF; chưa thiết bị vật lý |
| 5 AI | structured validation, model/prompt provenance, bốn request thật, human review |
| 6 Bảo mật/đạo đức | hash/quyền/CSRF/PII; không thay kiểm toán bảo mật độc lập |
| 7 Hiệu năng | mẫu tuần tự local và test cạnh tranh; không tuyên bố SLA |
| 8 Triển khai | Docker/lock/CI/Render; hạn Free và backup runbook |
| 9 Báo cáo | technical-report.md, data-dictionary.md, ai-usage-log.md |
| 10 Demo | demo-script.md, slide và dữ liệu giả; sinh viên cần diễn tập/trình bày thật |
