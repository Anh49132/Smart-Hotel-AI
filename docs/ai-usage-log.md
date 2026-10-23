# Nhật ký AI và kiểm chứng

Các mục dưới đây ghi công việc thực tế trong phiên hỗ trợ, không dựng lại lịch sử trước đó.

## R01 — PostgreSQL

- Yêu cầu: thực hiện 5 commit đầu của kế hoạch, giữ nhánh `feature/...` và phân công hai email đã xác nhận.
- AI hỗ trợ: phân tích URL/driver, phát hiện enum `bookingstatus` bị tạo lại ở migration 0002 trên PostgreSQL, sinh công cụ chuyển từ snapshot SQLite vào đích rỗng, kiểm tra số dòng/tổng tiền và sequence.
- Quyết định kiểm soát: không đọc/in key, không dùng database dự án khác, không tự đổi DATABASE_URL local, không ghi đè đích có dữ liệu.
- Kiểm chứng: test URL, chuyển dữ liệu và migration; kết quả thực tế được ghi trong báo cáo hoàn thành sau mỗi phần.

## C01 — Toàn vẹn dữ liệu

- AI hỗ trợ bỏ ba bộ hàm bị định nghĩa trùng, kiểm tra tham chiếu ở service và ràng buộc miền dữ liệu ở DB.
- Điều chỉnh sau kiểm tra: SQLite cần tắt FK ngoài transaction trong thao tác batch migration, rồi kiểm tra toàn bộ FK trước commit; không chỉ bật PRAGMA ở ứng dụng.
- Kiểm chứng: PostgreSQL/SQLite, từ chối khách/loại phòng không tồn tại, chặn xóa lịch sử, ghi SQL trực tiếp sai ràng buộc và nâng DB SQLite có lịch sử/hóa đơn.

## C02 — Đặt phòng và chuyển trạng thái

- AI hỗ trợ thiết kế khóa trên phòng trước đọc phòng trống: PostgreSQL khóa hàng, SQLite lấy khóa ghi bằng UPDATE không thay dữ liệu. Cùng thứ tự khóa được dùng cho nhận/trả, trạng thái phòng và ghi dịch vụ.
- Sửa unique ngày tuyệt đối bằng migration giữ lịch sử, hủy lịch tương lai không đổi tình trạng vật lý, check-in yêu cầu phòng sẵn sàng và không có khách khác.
- Kiểm chứng hai session thật chạy đồng thời: đặt chồng lịch, nhận phòng lặp và checkout cùng ghi dịch vụ; sát biên/đặt lại sau hủy vẫn hợp lệ. Test chạy trên cả PostgreSQL và SQLite.

## C03 — Giá đã chốt và hóa đơn

- Lưu đơn giá tại xác nhận booking; bản cũ có hóa đơn suy ra giá từ tiền phòng/số đêm, bản chưa có hóa đơn dùng giá hiện tại và đánh dấu nguồn `legacy_current_rate` (không khẳng định là giá lịch sử).
- Giữ giảm giá khi tính lại/checkout, làm mới dịch vụ trước chốt, giữ nguyên tổng tiền phòng của hóa đơn lưu trú đã hoàn tất. Ràng buộc tổng, giảm giá và tiền thu tại DB.
- Kiểm chứng: thay giá niêm yết, thêm dịch vụ sau lập hóa đơn tạm, giảm giá âm/quá tổng/sai độ chính xác, tổng 0, thu đồng thời và đối chiếu từng Payment. API tiền dùng Decimal tối đa hai chữ số thập phân.


## C04 — Tài khoản nhân sự và phiên đăng nhập

- AI hỗ trợ thêm version cho JWT, kiểm tra tài khoản khóa khi login, đổi/reset mật khẩu, bắt buộc đổi mật khẩu tạm và quản trị vai trò; giữ phạm vi nội bộ khách sạn.
- Kiểm soát: mật khẩu băm bcrypt, giới hạn 72 byte; production chặn secret/mật khẩu mẫu, không tự tạo schema/seed; cookie Secure và giới hạn đăng nhập một worker. Không ghi mật khẩu, key hoặc token thực vào Git.
- User bổ sung Git Flow trong lúc thực hiện: tạo dev từ main, nhập R01/C01/C02/C03 bằng merge commit; C04 phát triển trên feature/c04-staff-security và nghiệm thu vào dev. Chưa có review/PR GitHub; không dựng lịch sử review cho hai tài khoản.
- Test: thu hồi token sau đổi/reset/khóa/đổi quyền, đổi mật khẩu tạm, tự bảo vệ admin, ma trận ba vai trò, cookie/Origin, giới hạn login và migration. Kết quả cả bộ được cập nhật sau chạy.

- Kết quả đợt R01–C04: SQLite 82 passed/2 skipped; PostgreSQL 84 passed, gồm migration roundtrip, transfer và đồng thời. DB local 0002→0006 đã có backup, đối chiếu số dòng/tổng tiền và kiểm tra FK/integrity đạt. Không deploy hoặc gọi Gemini thật trong bộ test.
