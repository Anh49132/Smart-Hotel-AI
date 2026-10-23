# Kịch bản demo 8–10 phút

Trước giờ báo cáo: mở web Render trước để đánh thức, kiểm tra `/healthz`, Gemini còn quota, đăng nhập từng vai trò bằng mật khẩu riêng đã đổi; chuẩn bị local dự phòng. Chỉ dùng dữ liệu giả. Không mở trang env, token, DB URL hoặc giấy tờ thật khi chia sẻ màn hình. Không seed lại hoặc reset dữ liệu trong buổi demo.

| Thời gian | Thao tác | Điều cần giải thích |
|---|---|---|
| 0–1 phút | Giới thiệu phạm vi, vai trò và kiến trúc | App nội bộ một khách sạn, nhân viên vận hành |
| 1–3 phút | Lịch ngày/loại/khách; AI tư vấn; tạo booking từ ô lịch | Phòng trống lọc tại backend, AI không giữ phòng |
| 3–4 phút | Thu cọc trực tiếp, nhận phòng | Tiền được ghi sổ, chống bấm lặp; lịch khác trạng thái vật lý |
| 4–6 phút | Thêm dịch vụ; xem đổi phòng/lịch; trả phòng; thu còn lại | Giá từng đêm và bảng kê/tiền cọc đối chiếu, xuất PDF |
| 6–7 phút | Buồng phòng dọn và kiểm tra; xem hủy có phí/hoàn ở mẫu có sẵn | Phân quyền và audit; không xóa giao dịch |
| 7–9 phút | Email nháp, duyệt; báo cáo kỳ và nhận xét Gemini | Không gửi email tự động; số liệu do code xác minh |
| 9–10 phút | Minh chứng test, backup/restore, Git Flow và giới hạn | Phân biệt mock/AI thật, Free/cold start và hạn DB |

Đường dự phòng: khi AI hết quota, cho xem lỗi thân thiện rồi mở bản nháp/evaluation đã lưu; không giả kết quả đang gọi thật. Khi Render ngủ/mất mạng, chuyển bản Docker/local có cùng dữ liệu giả; nói rõ môi trường. Sau demo lưu backup, không xóa hồ sơ để làm lại.

## Câu hỏi bảo vệ

- **Vì sao không đặt trùng?** Khoảng nửa mở, cùng truy vấn availability, kiểm tra lại trong transaction có khóa, test hai yêu cầu cạnh tranh.
- **Sửa giá có thay tiền booking cũ?** Không, chụp giá từng đêm/chặng. Thay đổi booking dùng nghiệp vụ có lịch sử.
- **Thu tiền hai lần khi mạng chậm?** Khóa request tài chính + kiểm tra số dư/transaction; UI khóa bấm chỉ hỗ trợ UX.
- **Vì sao doanh thu khác thu tiền?** Hóa đơn theo mốc phát sinh, cọc/thu/hoàn theo ngày giao dịch. Số thu cũ thiếu ngày được tách legacy, không tự gán ngày.
- **AI bịa phòng/con số thì sao?** JSON schema và đối chiếu dữ liệu backend, sai bị từ chối; email tự do vẫn phải duyệt.
- **Đã gửi dữ liệu gì cho Gemini?** Phòng trống/giá, booking tối thiểu hoặc tổng số liệu được chọn; không giấy tờ/thông tin thanh toán/ghi chú tùy ý.
- **Nhân viên đăng ký tài khoản thế nào?** Quản trị viên tạo tài khoản và cấp vai trò trong màn Nhân sự; nhân viên đổi mật khẩu lần đầu. Chưa có trang tự đăng ký công khai.
- **Rollback thế nào?** Chỉ artifact hỗ trợ schema hiện tại. Restore DB mới từ archive/manifest có kiểm tra; không downgrade tùy tiện.
- **Render Free đủ không?** Đủ phạm vi demo đã thử; ngủ/quota/hạn DB vẫn tồn tại, không cam kết production SLA.
- **Hai người làm gì?** Mở kế hoạch và commit thật. Nói rõ coding agent hỗ trợ; không coi tác giả Git là bằng chứng review/diễn tập đã xảy ra.

Hai thành viên cần tự phân vai trình bày, kiểm tra hiểu code của nhau và diễn tập đúng thao tác. Tài liệu này là kịch bản, chưa phải xác nhận đã diễn tập.
