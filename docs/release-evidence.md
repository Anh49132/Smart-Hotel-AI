# Nghiệm thu bản bàn giao · 23/10/2026

- Python 3.14.7, requirements.lock; `pip check` và compileall đạt.
- Full suite PostgreSQL: **165 passed**, 164,44 giây. SQLite: **163 passed, 2 skipped**, 133,53 giây. Hai skip là migration/transfer dành PostgreSQL. Test dùng DB/schema riêng, không chạy trên Render hay dữ liệu khách thật.
- Có cảnh báo deprecation từ stack hiện tại (2149/2148 warnings); không ghi là không có cảnh báo. Nâng dependency/framework cần một đợt hồi quy riêng.
- Backup/restore: xem backup-restore-evidence.json. Đối chiếu số dòng, hóa đơn/sổ tiền, 23 sequence, revision 0022; đích có bảng bị từ chối.
- Lỗi transfer bảng demo_seeds dùng khóa tự nhiên được phát hiện trong full suite, sửa và thêm dữ liệu regression trước vòng chạy cuối.
- SQLite local backup `data/hotel.before-c19-c24.20261023-195346.db`, nâng 0016→0022; số dòng bảng cũ/từng giá trị hóa đơn, integrity/FK giữ đúng. Backup chứa dữ liệu riêng và không được commit.
- Browser desktop/mobile và PDF: docs/demo-data-and-ux.md, docs/images, output/pdf. AI live: bốn request dữ liệu giả trong ai-live-evaluation-2026-10-23.json.
- Docker build và test SQLite/PostgreSQL trên CI Linux đã success ở hai run được ghi trong render-release.md; kết quả local không thay kết quả cloud.
- Render artifact đầu đã live, smoke thật đạt 18 mục gồm Gemini và PDF; UI online và persistence qua redeploy ghi riêng trong render-release.md, render-smoke-evidence.json và render-persistence-evidence.json.
