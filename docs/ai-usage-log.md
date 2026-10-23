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


## C05 — Loại phòng và giá theo ngày

- AI hỗ trợ CRUD loại phòng, ngừng bán giữ lịch sử, giá thường/cuối tuần và chương trình giá đặc biệt theo khoảng [bắt đầu, kết thúc). Thứ Bảy/Chủ nhật là cuối tuần; giá đặc biệt ưu tiên cao nhất, không cho hai khoảng đặc biệt đang áp dụng trùng nhau.
- Khóa loại phòng trước khi sửa giá/kiểm tra khoảng trùng; booking khóa phòng rồi loại phòng, lưu từng đêm vào booking_nights. Hóa đơn dùng tổng snapshot; giá trung bình chỉ để tương thích hiển thị. Legacy không tự bịa giá từng đêm, tiếp tục dùng giá đã lưu ở 0005.
- Giao diện /rates cho admin, backend kiểm tra sức chứa với booking hiệu lực. Phòng ngừng bán không được đặt mới hoặc gợi ý AI; booking cũ vẫn phục vụ. AI kiểm tra ngân sách cho từng đêm thực tế.
- Kiểm chứng: giá cuối tuần/ngày đặc biệt, sát biên, bảng giá trùng đồng thời, sửa bảng giá sau đặt, thiếu snapshot, sức chứa, ngừng bán, quyền và migration SQLite/PostgreSQL. Không gọi Gemini thật.

- Kết quả C05: toàn bộ SQLite 90 passed/2 skipped; PostgreSQL 92 passed trên schema riêng. Chưa triển khai Render.


## C06 — Chi tiết đặt phòng

- AI hỗ trợ tách service chỉ đọc, API GET /api/bookings/{id} và trang /bookings/{id}; liên kết từ danh sách/tổng quan/hóa đơn. Một trang tập hợp giá đã chốt, khách, dịch vụ, hóa đơn, lịch sử trạng thái và khoản thu.
- Kiểm soát: không tạo hóa đơn khi xem, phân biệt dự tính với hóa đơn tạm, giữ nguyên hóa đơn chốt. Không xuất số giấy tờ/hash mật khẩu; Jinja escape ghi chú. Lịch sử thu tiền chỉ cho admin/kế toán, nút nghiệp vụ kiểm tra quyền/trạng thái cả UI và backend.
- Người dùng yêu cầu thử tạo/push C06 bằng đăng nhập GitHub thật của Khanh; tác giả commit Khanh và tài khoản push được xác minh riêng, không dùng tên/email Git để giả định tài khoản push.
- Kiểm chứng C05+C06: PostgreSQL 100 passed; SQLite 98 passed/2 skipped. Test cả luồng lưu trú, ba vai trò, dữ liệu trống/legacy/hủy/không tồn tại, XSS ghi chú, chênh lệch lịch sử thu và không có tác dụng phụ khi xem. Không gọi Gemini thật.
- DB local đã sao lưu trước C05, nâng 0006→0007, đối chiếu số dòng/tổng hóa đơn và FK/integrity đạt; các trang đã render bằng DB local và JavaScript nội tuyến được kiểm tra cú pháp bằng Node. Chưa thực hiện kiểm thử tương tác trình duyệt hoặc triển khai Render trong đợt này.


## C07 — Sửa lịch, gia hạn và đổi phòng

- Thêm room_stays và audit booking_changes; migration backfill chặng từ lịch cũ. Mọi truy vấn phòng trống/AI dùng các chặng, có fallback cho bản ghi legacy chưa có chặng.
- Khóa phòng theo thứ tự ID rồi booking/loại phòng, yêu cầu preview + expected_total; xung đột hoặc tổng hóa đơn thấp hơn tiền đã thu rollback toàn bộ. Giá đêm đã ở được giữ, đổi phòng đang ở có hiệu lực hôm nay Asia/Bangkok; phòng cũ cần dọn. Dữ liệu legacy thiếu giá đêm phải đối chiếu trước khi đổi khi đang ở.
- API/giao diện chi tiết hỗ trợ xem giá và xác nhận, hiển thị các chặng và audit. Kiểm tra phòng vừa thay đổi để các thao tác đồng thời không sửa tình trạng phòng cũ.
- Test thay đổi xác nhận, lỗi trùng rollback, đổi giữa kỳ/giữ giá, sát biên, giá cần xác nhận, quyền/render và migration. SQLite nhóm C07/detail/migration 13 đạt, 1 bỏ qua PostgreSQL; nhóm PostgreSQL và toàn bộ hồi quy được ghi ở cuối đợt C07–C12.


## C08 — Lịch phòng

- API/HTML lịch theo chặng phân phòng, ngày trả loại trừ; bộ lọc ngày/loại/tầng/số khách, phân trang 20 phòng và tối đa 31 ngày. Ô trống liên kết đặt phòng với ngày/phòng điền sẵn; mã lịch mở chi tiết lưu trú.
- Giao diện cuộn ngang và cột/tiêu đề cố định, không triển khai kéo thả khi chưa có kiểm chứng xung đột tương đương. Filter phòng trống có tham số loại/tầng ở backend.
- Nhóm test SQLite lịch + C07: 5 đạt, gồm sát biên, bộ lọc, trống và chưa đăng nhập. Kiểm thử tương tác browser và toàn bộ hồi quy ghi ở cuối đợt.


## C09 — Buồng phòng và kiểm tra sẵn sàng

- Thêm role housekeeping và task pending→in_progress→inspection→ready; checkout/đổi phòng tạo việc trong cùng transaction. Khóa phòng khi phân công/chuyển trạng thái, chỉ supervisor kiểm tra cuối, không cho đặt trạng thái sẵn sàng để bỏ qua việc chưa hoàn tất.
- Housekeeping chỉ truy cập việc được giao và tài khoản cá nhân, không nhận khách/hóa đơn/AI. UI theo vai trò, admin cấp tài khoản buồng phòng. Migration giữ các phòng cleaning cũ dưới dạng pending, không dựng thời gian hoàn thành.
- Test checkout→phân công→dọn→kiểm tra, chặn vượt quyền/API và render; kiểm tra enum PostgreSQL với migration roundtrip. Downgrade từ chối nếu còn tài khoản housekeeping thay vì làm mất dữ liệu vai trò.


## C10 — Bảo trì và khóa bán theo ngày

- Phiếu sự cố có người phụ trách, trạng thái và thời gian xử lý; khoảng khóa [bắt đầu,kết thúc) không được chồng booking/khóa hiện có. Tạo block và tạo booking khóa cùng phòng để tránh race.
- Inventory chung cấp cho đặt/sửa booking, API phòng trống, lịch và AI; phòng dọn chưa được kiểm tra sẵn sàng khi còn khóa hôm nay. Khóa hết khoảng ngày không chặn lịch tương lai. Trạng thái vật lý maintenance thủ công vẫn là khóa vô thời hạn cho tới xử lý.
- Test cả ba đường phòng trống/lịch/AI, không ghi đè booking, sát ngày cuối và hai session tạo block cùng booking; kèm migration PostgreSQL/SQLite.


## C11 — Bàn lễ tân và no-show

- Bảng khách đến/đi/đang ở, quá giờ và tiền còn phải thu; walk-in đi qua tạo booking rồi nhận. Giờ Asia/Bangkok từ core/hotel_time, chỉ check-in trong khoảng ngày đã đặt; thời điểm nhận/trả thực tế được ghi.
- No-show là trạng thái riêng, chỉ sau giờ cấu hình của ngày đến, không đổi tình trạng vật lý phòng. Có hóa đơn phải xử lý tài chính trước khi no-show. Các báo cáo không tính no-show vào công suất.
- Phụ thu cố định một lần/lưu trú cho từng loại nhận sớm/trả muộn; nhân viên xác nhận đúng mức đang cấu hình, lưu snapshot và người xác nhận. Không tự cộng phí khi xem. Hóa đơn có cột phụ thu riêng, constraint tổng/giảm giá được nâng cấp giữ nguyên tổng cũ.
- Test thời điểm sát giờ no-show, trước ngày nhận bị chặn, phí không tự áp dụng/không lặp/giá đổi phải xác nhận lại, checkout và migration. Đồng hồ test được cố định 2030-01-10 thay vì phụ thuộc ngày chạy.


## C12 — Lịch sử khách và riêng tư

- AI hỗ trợ tìm/phân trang khách và lịch sử, đếm checked_out thay vì tất cả booking, ngày hoàn tất ưu tiên actual checkout theo Asia/Bangkok; chuyển phòng không làm tăng lượt. Preferences chỉ cho admin/lễ tân và không gửi AI.
- Che giấy tờ trong API/HTML mặc định, endpoint đối chiếu riêng kiểm tra quyền và no-store; sửa thông tin trống giữ giấy tờ/ghi chú cũ, xóa giấy tờ cần cờ rõ. Schema đầu ra booking/invoice whitelist để tránh quan hệ ORM vô tình mang giấy tờ theo response.
- Review tích hợp bổ sung UI sẵn sàng theo ngày/task/block, thông báo validation đọc được, bỏ điền sẵn mật khẩu ở login và không hiện tài khoản mẫu trong production, bảng vận hành cuộn ngang ở màn hình hẹp.
- Kết quả cuối C07–C12: PostgreSQL 117 passed; SQLite 115 passed/2 skipped. Hai session thực kiểm tra đổi vào cùng phòng, lịch rút ngắn dưới tiền đã thu rollback; có test privacy ba vai trò, sequence fixture PostgreSQL được sửa sau khi phát hiện explicit ID không tăng sequence.
- Browser QA dùng DB dữ liệu giả riêng: ô lịch điền sẵn phòng 304/ngày, preview rồi đổi phòng thành công; phát sinh việc phòng 301 và đi hết start→complete→inspect; lịch sử khách 1 đã ở + 1 đang ở, giấy tờ che; bộ lọc bàn lễ tân; tài khoản housekeeping chỉ thấy việc được giao, không có menu khách/hóa đơn/AI.
- DB local backup hotel.before-c07-c12.20261023-124227.db, nâng 0007→0012, giữ số dòng bảng cũ và tổng tiền hóa đơn, Alembic check/FK/integrity đạt. Không triển khai Render, không gọi Gemini thật, không gửi email trong đợt này.


## C13 — Thu cọc và sổ thu tiền

- Thêm money_entries làm sổ chuẩn; Payment cũ chỉ là mirror tương thích, không cộng cùng ledger. Thu cọc trước hóa đơn, khi lập/checkout đối trừ đúng số đã nhận. Phương thức cash/bank_transfer, mã tham chiếu và người thu; không có trường số thẻ/tài khoản.
- Các API ghi tiền yêu cầu request_key, body cùng khóa trả cùng biên nhận; đổi nội dung với cùng khóa bị chặn. Khóa phòng→booking→invoice theo một thứ tự; quá số dư bị từ chối cả khi thu đồng thời.
- Migration nhập Payment hiện có một lần, chênh paid_amount chưa có lịch sử thành legacy_opening có nhãn thời điểm thực không biết. Nếu Payment lớn hơn paid_amount thì dừng để đối chiếu, không tự bịa khoản hoàn. Downgrade từ chối bỏ dữ liệu giao dịch mới.
- Phát hiện wildcard action route nuốt đường thu cọc; tách các route nhận/trả/hủy rõ ràng. UI giữ mã chống lặp của lần gửi và chặn bấm lặp. Test cọc một phần/đối trừ, retry, cùng khóa đồng thời, quá số dư và migration số dư cũ; toàn bộ hồi quy được ghi cuối đợt.


## C14 — Bảng kê và chứng từ nội bộ

- Tách dòng chi phí khỏi sổ tiền: từng đêm/chặng, dịch vụ snapshot, phụ thu, giảm giá; cọc/thu/hoàn ở bảng riêng để không trừ/cộng hai lần. Dữ liệu legacy/chênh hóa đơn có dòng đối chiếu rõ, không dựng chi tiết giả.
- HTML in từng lưu trú/phiếu thu độc lập Bootstrap, A4/@media print, không giấy tờ/thông tin thẻ. Ghi rõ chứng từ nội bộ, không phải hóa đơn điện tử. Lễ tân chỉ in phiếu cọc do mình ghi; bảng kê/sổ giao dịch dành cho admin/kế toán.
- Test tổng dòng bằng tổng hóa đơn, đối trừ cọc đúng, mở trang không tạo tiền và quyền in. Kiểm tra bản in trong trình duyệt và toàn bộ hồi quy ghi cuối đợt.


## C15 — Quyết toán hủy/no-show và hoàn tiền

- Chính sách phần trăm trên tổng hóa đơn trước điều chỉnh, snapshot mức phí/người/lý do khi xác nhận sau preview. Không xóa hóa đơn/giao dịch cũ; financial_adjustments giữ tổng gốc và khoản giảm về phí phải trả.
- Sổ tiền thêm refund với lý do, phương thức, tham chiếu và idempotency. Hoàn tối đa số đã nhận ròng; lịch hủy/no-show giữ lại phí đã chốt. Refund chủ động khi lịch còn hiệu lực làm tăng công nợ, không tự giảm phí lưu trú. Không chuyển tiền tự động.
- Hủy/no-show sau thu cọc chỉ đi qua quyền admin/kế toán; trạng thái physical phòng không bị ghi đè. Bảng kê/danh sách hóa đơn hiển thị tổng hiệu lực, số dư âm là còn phải hoàn. Phiếu hoàn riêng.
- Test hoàn một phần, retry, hoàn đồng thời, giữ phí, đồng hồ no-show và tổng dòng bảng kê; migration kiểm tra cả SQLite/PostgreSQL. Kết quả toàn bộ ghi cuối đợt.
