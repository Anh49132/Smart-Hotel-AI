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


## C16 — Ca thu ngân và bàn giao
- Prompt: “Gắn thu/hoàn vào ca đang mở, tính két tiền mặt và khóa ca khi chốt; kiểm tra cuộc đua thu tiền với chốt ca.”
- Triển khai: chỉ một ca mở mỗi nhân viên (ràng buộc DB); khóa ca khi ghi tiền/chốt; chuyển khoản tách khỏi két, hoàn tiền mặt không vượt tồn két. Chốt lưu số kiểm đếm, chênh lệch, người nhận, ghi chú và ảnh chụp số liệu/công việc tồn.
- Chỉnh sửa/kiểm chứng: replay giao dịch cũ sau đóng ca vẫn trả kết quả cũ; giao dịch mới bị chặn. Dữ liệu thu cũ để shift_id trống vì không có bằng chứng ca thực tế. Fixture kiểm thử mở ca rõ ràng; ứng dụng không tự mở ca.
- Kiểm thử: PostgreSQL cho thu/hoàn/cọc, migration round-trip, chốt ca đồng thời và bảng kê.


## C17 — Báo cáo vận hành và đối soát
- Prompt: “Tách doanh thu hóa đơn khỏi dòng tiền; tính công suất theo room-night/chặng đổi phòng và lịch bảo trì; công bố mốc thời gian.”
- Triển khai: khoảng ngày nửa mở, UTC+7 cho giao dịch; hóa đơn theo ngày phát hành, điều chỉnh theo ngày quyết toán, thu/hoàn theo ngày giao dịch. Không cộng Payment mirror; legacy_opening chưa rõ ngày thu không tính vào dòng tiền.
- Công suất theo lịch (gồm confirmed), không gán nhãn đêm thực ở; trừ hợp các room-day khóa bảo trì, cảnh báo lịch chồng khóa; công nợ/cọc chưa phân bổ là ảnh chụp hiện tại, không giả dữ liệu lịch sử.
- Kiểm chứng: PostgreSQL kiểm thử qua tháng, chặng đổi phòng, loại no-show, bảo trì trùng, ranh UTC+7, hoàn tiền, điều chỉnh khác ngày hóa đơn, CSV không chứa thông tin khách.


## C18 — Gemini chọn phòng bằng JSON có kiểm chứng
- Prompt: “Model chỉ xếp hạng ID trong inventory đã lọc; kiểm tra schema, ID, giá, tiện ích và truy vấn lại sau lúc chờ model. Không để văn bản model tự tạo giá/phòng.”
- Tham chiếu API chính thức: https://ai.google.dev/api/generate-content#v1beta.GenerationConfig (responseMimeType/responseJsonSchema).
- Thay đổi: Pydantic giới hạn ba lựa chọn, tổng tiền khớp Decimal, mã lý do trong tập cho phép; backend dựng câu trả lời/giá. Tiện ích lọc đủ các thuật ngữ; không đáp ứng thì không gọi AI. Không gửi hồ sơ khách.
- Kiểm chứng: mock transport/schema, bịa phòng/giá, phòng trùng, sai JSON, ngân sách thấp, ngày sai, chèn lệnh/tiện ích không có, bảo trì và booking phát sinh khi model xử lý. Không gọi model thật.
- Review tích hợp: chặn hủy/no-show nhanh bỏ qua phí; kiểm tra quyền hoàn/chốt ca khác người; chuyển khoản không thành tồn két. Fixture tái tạo schema PostgreSQL hủy pool để bỏ prepared plan cũ sau khi enum OID đổi; không sửa cấu hình production để che lỗi test.
- Browser QA DB giả: bảng kê khớp tổng/cọc, preview hủy, chốt ca 600.000 tiền mặt lệch 0, báo cáo phân biệt 1.800.000 hóa đơn và 500.000 thu. IAB chưa xác minh được preview in; không coi là test máy in/PDF xuất thực tế.


## C19 — Email nghiệp vụ và lịch sử duyệt
- Prompt: “Soạn email theo trạng thái xác nhận/hủy/thay đổi/nhắc tiền, lấy dữ liệu tối thiểu; lưu model/prompt và giữ lịch sử duyệt.”
- Triển khai: từ chối loại email trái trạng thái, nhắc tiền khi hết nợ, thông báo đổi khi chưa có thay đổi; kiểm tra snapshot lại sau model. Không gửi giấy tờ, liên hệ, sở thích, ghi chú hoặc tài khoản thanh toán.
- Migration 0019 ghi model/prompt/source có chọn lọc; dữ liệu cũ mang legacy/unknown. Duyệt có khóa và event append-only; lễ tân chỉ xem/in bản nháp của mình, admin/kế toán duyệt. Bản nháp có sao chép/in, không tự gửi email.
- Kiểm chứng: các loại email, dữ liệu riêng tư, race đổi trạng thái, hai người duyệt đồng thời, quyền xem và bản in; regression Gemini/business/migration SQLite đạt (PostgreSQL nghiệm thu tổng ở C21).


## C20 — Báo cáo/ca có nguồn số liệu và giới hạn AI
- Prompt: “Chọn key/value chỉ số và mã ý tưởng khuyến mại từ schema; backend từ chối số liệu khác snapshot. Tóm tắt ca chỉ trong phạm vi được xem.”
- Triển khai: dùng C17, tách mốc thời gian/số dư hiện tại; model chỉ chọn trọng tâm, code dựng mọi con số và gợi ý cần quản lý duyệt. Ca không gửi ghi chú, tên nhân viên, mã tham chiếu hoặc dữ liệu khách. Lễ tân không nhận tổng công nợ khách sạn trong chat. Giới hạn một tiến trình: 10 yêu cầu AI/phút/người, tối đa hai đang xử lý; context chat giữ giới hạn 12 lượt và 1500 ký tự/lượt.
- Mock: giá trị bịa bị từ chối, quyền ca/báo cáo, không truyền ghi chú và budget đồng thời. Ba lượt gọi Gemini thật bằng DB giả đã đạt: gợi ý phòng, báo cáo và email; bằng chứng trong ai-live-evaluation-2026-10-23.json. Email vẫn cần người duyệt.
- Phát hiện từ thử thật: bộ lọc giấy tờ có thể che nhầm booking code dạng BK-A1234567. Đã bảo vệ riêng mã booking lấy từ DB trước lọc, không nới bộ lọc giấy tờ; bổ sung test hồi quy.

Đã gọi thêm đúng một lượt email sau sửa bộ lọc: mã BK-A1234567 được giữ và ngày/loại phòng khớp dữ liệu giả. Tổng đợt đánh giá bốn request; kết quả lần đầu và lỗi đã sửa đều được giữ, không xóa minh chứng.


## C21 — Nghiệm thu tích hợp, quyền và hiệu năng demo
- Prompt: “Kiểm thử cả quy trình nhiều vai trò; đối chiếu ca/folio/báo cáo sau đổi phòng, cọc và thu cuối; đo dữ liệu demo bằng schema riêng.”
- Bổ sung luồng acceptance nhiều vai trò và ma trận quyền. Giữ các test đồng thời/migration đã có, không thay bằng smoke test. Sửa danh sách phòng từ chuỗi HTML sang Option.text an toàn.
- Kết quả: PostgreSQL 157 đạt; SQLite 155 đạt/2 bỏ qua. Benchmark PostgreSQL riêng 30 phòng/120 booking, 72 GET đều 200, tối đa 68,21 ms trong mẫu tuần tự local; không suy diễn tải production. Chi tiết tại acceptance-c21.md và benchmark JSON.


## C22 — Dữ liệu demo, UX và PDF
- Prompt: “Seed dữ liệu giả đủ các trạng thái và tài chính, chạy lại không reset; hoàn thiện tìm kiếm toàn CSDL, responsive, lỗi mạng và bản in tiếng Việt.”
- Seed chỉ dành cho khách sạn demo chưa có dữ liệu, có marker; nhân sự có mật khẩu riêng/đổi lần đầu. Dữ liệu mẫu không làm thay đổi CSDL local thật. Kiểm thử idempotency, số dư và folio trên PostgreSQL đạt.
- Phân trang/tìm server booking/hóa đơn, khóa form thường, timeout có thông báo, local Bootstrap/Icon/font và giấy phép; dashboard phân biệt sẵn sàng vật lý với phòng trống theo lịch, thu ròng từ MoneyEntry.
- Browser 390×844/1366×900: menu, bảng/lịch, tìm booking ngoài trang đầu, chọn ô lịch và tạo booking QA thành công. PDF có nhúng font/escape/quyền/no-store; xuất và render hai mẫu qua Poppler, sửa khối chữ ký thành hai cột sau kiểm tra hình ảnh. Chưa kiểm tra điện thoại/máy in vật lý.

## C23 — Đóng gói và phục hồi
- Prompt: “Đóng gói Docker một worker, kiểm tra sức khỏe CSDL, giới hạn body, CI; backup PostgreSQL cùng snapshot và restore đích rỗng có đối chiếu.”
- Docker chạy non-root, ghim Python digest và dependency lock; secrets chỉ ở môi trường. Startup chạy Alembic có khóa, production từ chối SQLite. Health check SELECT 1, trả lỗi chung; request body giới hạn 64 KB trước parser.
- pg_dump/pg_restore chạy thật trên hai database QA mới ở localhost. Phát hiện đường dẫn Windows tiếng Việt và public schema có sẵn; sửa dùng binary stream và TOC bỏ riêng CREATE SCHEMA public. Restore nguyên tử, không --clean, từ chối đích đã có bảng. Đối chiếu 21 booking/12 phòng, tổng tiền, 23 sequence, revision 0022; bằng chứng backup-restore-evidence.json.
- SQLite local được backup trước nâng 0016→0022; số dòng bảng cũ và từng giá trị hóa đơn giữ nguyên, integrity/FK đạt. Không chuyển dữ liệu thật lên Render.
- Workflow CI được bổ sung cho PostgreSQL/SQLite và Docker. Không coi việc tạo workflow là kết quả CI đã đạt. Rollback code chỉ dùng artifact tương thích migration; không tự downgrade dữ liệu vận hành.
