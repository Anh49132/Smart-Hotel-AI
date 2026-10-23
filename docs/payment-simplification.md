# Thanh toán trực tiếp, bỏ ca thu ngân

Theo yêu cầu người dùng, bỏ phần mở/chốt ca thu ngân vì đề AIA331 không bắt buộc. Không còn menu/trang `/shifts`, API `/api/shifts` hoặc `/api/ai/handover/{id}`. Thu cọc, thanh toán và hoàn tiền thực hiện trực tiếp từ booking/hóa đơn.

Giữ kiểm tra vai trò, số dư/giới hạn thu và hoàn, transaction/khóa booking, mã chống xử lý lặp, người thực hiện, phương thức, lý do và thời điểm giao dịch. Không còn đối chiếu tiền mặt theo két/ca; người thực hiện ghi phương thức và số tiền theo giao dịch thực tế.

Schema vẫn revision 0022. Bảng cashier_shifts, FK shift_id và bản nháp AI cũ giữ như dữ liệu lưu trữ, không xóa hoặc chuyển đổi sổ tiền. Giao dịch mới không gắn ca, seed mới không tạo ca; marker seed cũ không bị reset. Không cần migration dữ liệu.

Nghiệm thu local Python 3.14.7:

- PostgreSQL: **164 passed**, 152,90 giây; SQLite: **162 passed, 2 skipped**, 128,28 giây. Hai skip dành PostgreSQL. Còn cảnh báo deprecation trong stack.
- Fixture không mở ca. Toàn luồng nhiều vai trò vẫn thu cọc, nhận/đổi/trả phòng, thu còn lại, đối chiếu folio/báo cáo và dọn phòng.
- Regression test_payments_without_shifts.py kiểm tra UI/API ca đã gỡ và ca đóng cũ không chặn thu/hoàn, không sửa record/receipt lịch sử. Các test chống lặp, đồng thời, quyền và giới hạn tài chính vẫn chạy.
- README, báo cáo, ma trận, kịch bản demo và slide đã cập nhật. Các phần C16/C20 và nghiệm thu trước đó trong nhật ký/kế hoạch là lịch sử, không mô tả chức năng hiện hành.
