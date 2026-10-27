# Dữ liệu demo và giao diện C22

Chỉ bật `DEMO_MODE=true` cho CSDL minh họa riêng. Bật `DEMO_SEED_ON_START=true` và đặt `DEMO_STAFF_PASSWORD` riêng từ 12 ký tự (tối đa 72 byte UTF-8) để seed khi khởi động; hoặc chạy `python -m scripts.seed_demo` với DEMO_MODE và mật khẩu được cấu hình. Không ghi mật khẩu vào Git. Staff phải đổi mật khẩu tạm ở lần đăng nhập đầu. Production vẫn yêu cầu SECRET_KEY và BOOTSTRAP_ADMIN_PASSWORD riêng, không dùng Admin@123.

Seed v1 gồm 12 phòng/3 loại, 8 hồ sơ khách giả, 3 dịch vụ, 21 booking nền và 12 booking báo cáo cho tháng 8–11 của năm neo; có đủ confirmed/checked_in/checked_out/cancelled/no_show, cọc/thu/hoàn/điều chỉnh, một việc dọn và một khoảng bảo trì. Tên/mã có DEMO để nhận biết. Ngày neo là ngày khách sạn tại lần seed đầu; không tự dịch lịch sau mỗi lần khởi động. Bản đã seed trước đây được bổ sung 12 booking tháng một lần khi DEMO_MODE và DEMO_SEED_ON_START bật. Seed hiện tại không tạo ca thu ngân; bản demo đã seed từ trước giữ ca cũ như dữ liệu lưu trữ, không sử dụng trong thanh toán.

`demo_seeds` ghi marker. Chạy lại không đổi ngày, tạo trùng, reset mật khẩu hoặc sửa các booking nhân viên vừa tạo. Không cho seed mới vào nơi đã có phòng/booking. Cần một CSDL demo mới để làm lại hoàn toàn; không có nút xóa dữ liệu vận hành. Kịch bản ngày báo cáo nên tạo một booking mới theo ngày hiện tại từ phòng còn trống, không cố check-in lịch mẫu đã qua ngày.

Booking/hóa đơn tìm trên CSDL và phân trang 20 dòng; bộ lọc kết hợp với tìm kiếm. Các trang dữ liệu khác có phạm vi theo nghiệp vụ, calendar tối đa 31 ngày/20 phòng, customers 20 dòng. Asset Bootstrap/Icon phục vụ tại local, giấy phép đi kèm; font giao diện dùng hệ thống. Nút gửi các form thường có khóa khi đang xử lý; giao dịch tiền giữ request_key riêng. Lỗi mạng/timeout có thông báo; AI chờ tối đa 95 giây phía trình duyệt, endpoint nghiệp vụ 20 giây. Không tự gửi lại thao tác ghi khi chưa xác định kết quả.

Đã thử IAB ở viewport 390×844 và 1366×900: body không cuộn ngang, bảng/lịch cuộn trong vùng riêng; menu mobile mở được, tìm thấy DEMO-PAST01 ngoài trang đầu, nhấn ô lịch điền sẵn D301/ngày/số khách/giá và tạo booking QA #22 thành công. Ảnh trong images/browser-mobile.png, browser-desktop.png, browser-created-booking.png. Đây là viewport giả lập, chưa thay thế thử trên điện thoại thật.

PDF `/bookings/{id}/folio.pdf` và `/receipts/{id}/document.pdf` dùng quyền giống bản xem, no-store, font Noto Sans nhúng và escape nội dung. Tệp mẫu trong output/pdf dùng dữ liệu giả; đã render qua Poppler và kiểm tra tiếng Việt/dấu tiền, bố cục. Chưa thử máy in vật lý.
