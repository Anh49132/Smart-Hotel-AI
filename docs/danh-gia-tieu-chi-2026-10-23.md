# Đánh giá đáp ứng đề tài AIA331 — Hệ thống quản lý khách sạn tích hợp AI

> Đây là đánh giá đầu vào được giữ nguyên để đối chiếu lịch sử. Bản bàn giao sau C01–C24 xem [báo cáo kỹ thuật](technical-report.md), [ma trận minh chứng](traceability.md) và [nghiệm thu cuối](release-evidence.md). Không dùng các số test/trạng thái cũ bên dưới làm kết luận hiện tại.

Ngày kiểm tra: **23/10/2026**. Phạm vi: mã nguồn và cấu hình hiện có trong workspace, SQLite mặc định, kiểm thử tự động, migration và Ollama local. Đây là kết quả kiểm tra kỹ thuật, không phải điểm chấm của giảng viên.

**Cập nhật sau đánh giá:** theo yêu cầu chuyển nhà cung cấp, ứng dụng đã dùng Google Gemini thay Ollama. Bộ test sau chuyển đổi đạt **41/41**; thử API thật trên dữ liệu giả cho tư vấn phòng, email, báo cáo và chatbot đều trả HTTP 200. Các kết quả Ollama bên dưới là ghi nhận lịch sử trước chuyển đổi; xem README cho cấu hình AI hiện tại. Việc đổi nhà cung cấp không phải bằng chứng đã khắc phục các vấn đề đặt phòng, hóa đơn hoặc kiểm chứng đầu ra được nêu trong báo cáo.

**Kết luận: có phần lớn chức năng cốt lõi nhưng chưa đủ căn cứ xác nhận đáp ứng đầy đủ, ổn định cả 10 tiêu chí.** Cần ưu tiên chống đặt trùng khi đồng thời, toàn vẹn dữ liệu, chuyển trạng thái phòng, hóa đơn và AI thực tế trước khi bổ sung chức năng mới.

Không sửa mã nghiệp vụ hay dữ liệu khách sạn trong lần đánh giá này. Các thao tác tạo/xóa/thu tiền được thử trên SQLite tạm với dữ liệu giả. Dự án đã có thay đổi chưa commit từ trước; đánh giá dựa trên nội dung workspace, không chỉ phiên bản đã commit.

## 1. Bằng chứng kiểm tra

- Bộ test hiện có: **13 passed**, 340 cảnh báo deprecation, Python 3.14.7. Các cảnh báo không làm test thất bại.
- TestClient bị kẹt ở `socketpair` trong sandbox Windows; chạy lại ngoài sandbox đã đạt. Không tính sự cố sandbox là lỗi ứng dụng.
- Đã chạy thêm **14 tình huống kiểm tra cô lập**, gồm cả trường hợp đặt liên tiếp đúng biên và đặt chồng lịch đồng thời. Xem [kết quả thô](audit-results-2026-10-23.json).
- Trên database tạm: `alembic upgrade head` và `alembic check` đều thành công. Snapshot SQLite tạm có `integrity_check = ok`, cùng phiên bản migration. Chưa diễn tập khôi phục toàn bộ dữ liệu thực.
- Database hiện tại được đọc bằng chế độ chỉ đọc: revision `0002`; 1 tài khoản, 4 phòng, 2 loại phòng, 1 khách hàng, 2 đặt phòng, 3 dịch vụ, 1 hóa đơn. Các bảng lịch sử trạng thái, thanh toán chi tiết và kết quả AI đang trống. Không phát hiện vi phạm khóa ngoại trong dữ liệu hiện tại.
- Ollama `/api/tags` trả 200 và có `qwen2.5:latest`, phù hợp cấu hình `qwen2.5`. Tuy nhiên, gọi thật ba service tư vấn phòng, email xác nhận và báo cáo bằng dữ liệu giả đều phát sinh lỗi 503. Gọi trực tiếp `/api/generate` và `/api/chat` với prompt ngắn cũng gặp `ReadTimeout` ở ngưỡng 40 giây. Chưa xác định nguyên nhân gốc; không thể xem việc có model là bằng chứng AI hoạt động ổn định.
- Chưa kiểm tra giao diện bằng trình duyệt ở các kích thước màn hình, tải lớn, môi trường MySQL, cloud hoặc diễn tập thuyết trình. Test render HTML không chứng minh JavaScript và trải nghiệm thao tác đều đúng.

## 2. Đối chiếu chức năng của đề bài

| Yêu cầu | Tình trạng | Căn cứ và phần thiếu |
|---|---|---|
| Đăng nhập, admin/lễ tân/kế toán | Có, cần hoàn thiện | JWT, bcrypt, kiểm tra tài khoản hoạt động và quyền ghi đã có. Chưa có chức năng đổi mật khẩu; cần làm rõ quyền đọc thông tin nhạy cảm và nút thao tác theo vai trò. |
| Loại phòng, phòng, giá, trạng thái | Một phần | Có thêm loại phòng, CRUD phòng và đổi trạng thái. Chưa có API/giao diện sửa loại phòng, sức chứa, tiện ích và giá của loại phòng. |
| Khách hàng và lịch sử lưu trú | Có ở mức cơ bản | CRUD khách; giao diện có tổng lượt và ngày gần nhất. Tổng lượt đang đếm cả đặt phòng bị hủy/chưa lưu trú; chưa có màn hình chi tiết từng lần lưu trú. |
| Đặt/nhận/trả/hủy phòng | Có, có lỗi cần sửa | Có kiểm tra trạng thái và test luồng đầy đủ. Đặt lại sau hủy, nhận phòng bảo trì và hủy lịch tương lai có lỗi thực tế. |
| Phòng trống theo ngày, loại phòng, số khách | Một phần | Ngày và sức chứa đã lọc. API chưa khai báo bộ lọc loại phòng; truyền `room_type_id` bị bỏ qua. |
| Dịch vụ phát sinh | Có | Có giặt là, ăn sáng, đưa đón; chỉ ghi dịch vụ khi khách đang lưu trú; lưu đơn giá tại lúc sử dụng. |
| Hóa đơn và thanh toán | Có, có lỗi cần sửa | Decimal/Numeric, nhiều đêm, dịch vụ, trả từng phần, chống thu vượt và lịch sử thanh toán đã có. Còn vấn đề giá phòng, giảm giá và thu tiền cho lịch hủy. |
| Thống kê theo thời gian | Một phần | Có biểu đồ công suất/doanh thu 6 tháng. Chưa chọn khoảng ngày; thiếu thống kê số đặt phòng theo thời gian. Dashboard, báo cáo tháng và báo cáo AI dùng các định nghĩa/chân trời thời gian khác nhau. |
| AI tư vấn phòng | Có tích hợp, chưa đạt kiểm soát đầy đủ | Lọc phòng theo lịch/sức chứa/ngân sách trước khi gọi AI. Thiếu kiểm tra ngày và kiểm chứng đầu ra; chưa có kết quả gọi thật thành công trong lần kiểm tra. |
| AI email xác nhận/hủy/nhắc thanh toán | Có tích hợp, cần kiểm thử thật | Có ba loại và prompt, lưu bản nháp/duyệt; test mock xác nhận đã đạt. Chưa có test đủ hủy/nhắc/thay đổi phòng. Chỉ yêu cầu sinh email, nên không có gửi email SMTP không được tính là thiếu bắt buộc. |
| AI công suất/khuyến mại | Có tích hợp, cần kiểm thử thật | Có prompt và số liệu tổng hợp. Thiếu phạm vi ngày, kiểm chứng số liệu/nội dung và minh chứng đầu ra thật thành công. |
| Công nghệ | Đáp ứng lựa chọn của đề | FastAPI, HTML template/Jinja2, SQLite hoặc cấu hình MySQL, Ollama. Không bắt buộc chuyển sang React hoặc dùng AI có phí. |
| Test đặt phòng/trả phòng/hóa đơn/email AI | Đáp ứng tối thiểu | Đã có test cho bốn nhóm; độ bao phủ tình huống lỗi và đồng thời còn thiếu. |

## 3. Đối chiếu 10 tiêu chí cuối kỳ

| Tiêu chí | Đánh giá | Việc còn phải hoàn thiện |
|---|---|---|
| 1. Chức năng đầy đủ, ổn định | Đạt phần lớn luồng cơ bản | Sửa lỗi nghiệp vụ ở mục 4, hoàn thiện quản lý giá/loại phòng và bộ lọc loại phòng. |
| 2. Kiến trúc và mã nguồn | Có nền tảng tốt | Router/service/model/schema đã tách. Xóa các định nghĩa hàm trùng ở ba service; chuẩn hóa xử lý lỗi, response schema và mã frontend dài trên một dòng. |
| 3. Cơ sở dữ liệu | Đạt một phần | Migration và quan hệ đã có; cần bật khóa ngoại SQLite, ràng buộc miền dữ liệu và cơ chế chống trùng đồng thời. Seed phải nhất quán và đủ tình huống. |
| 4. Giao diện/UX | Có nền tảng, chưa xác nhận đầy đủ | Có Bootstrap, CSS responsive, modal, toast, loading AI. Cần kiểm thử trình duyệt/mobile, ẩn nút ngoài quyền, lịch phòng và lỗi validation dễ đọc. |
| 5. Chất lượng AI | Chưa đủ bằng chứng đạt | Sửa khả năng gọi model thực tế; kiểm chứng phòng đầu ra, ngày và ngân sách; đánh giá email/báo cáo bằng bộ tình huống rõ ràng. |
| 6. Bảo mật/quyền riêng tư/đạo đức | Đạt một phần | Cấu hình phiên hiện dùng khóa mẫu; có kênh chat chuyển nguyên văn dữ liệu người dùng sang model. Cần đổi khóa, đổi mật khẩu, lọc dữ liệu và thống nhất quyền đọc. |
| 7. Hiệu năng/ổn định | Chưa đủ | Đã tái hiện đặt trùng khi đồng thời; AI timeout. Chưa có kiểm thử tải; truy vấn danh sách chưa phân trang. |
| 8. Triển khai/đóng gói | Đạt cơ bản local | Có requirements, `.env.example`, launcher và hướng dẫn migration/backup. Chưa có Docker/cloud; đây là phần khuyến khích. Cần kiểm thử cài mới và chuẩn bị dữ liệu demo đủ. |
| 9. Báo cáo kỹ thuật | Chưa thấy đủ trong repository | Hiện có README và hướng dẫn migration; chưa thấy báo cáo phân tích, actor/use case, ERD, wireframe, ma trận test, đánh giá AI và nhật ký AI trong SDLC. Nếu tài liệu nằm ngoài repo cần tập hợp để đối chiếu. |
| 10. Thuyết trình/demo | Chưa thể xác nhận | Test luồng chính là điểm tốt nhưng chưa thấy kịch bản demo/slide/minh chứng đầu ra thật. Khả năng trình bày và trả lời cần đánh giá trực tiếp. |

## 4. Các vấn đề ưu tiên, có cách tái hiện

### P0 — Sửa trước khi xác nhận hệ thống ổn định

**A. SQLite vẫn đặt trùng khi có hai yêu cầu đồng thời.**

Nguồn: `backend/services/booking_service.py:24`, `core/database.py:18`.

Hai session cùng kiểm tra phòng trước khi ghi: lịch 10–12/01/2030 và 11–13/01/2030 đều được tạo. Probe đồng bộ hai thời điểm kiểm tra để tái hiện một cách xác định. `with_for_update()` không sinh `FOR UPDATE` với dialect SQLite; ràng buộc unique ngày bắt đầu/kết thúc cũng không chặn hai khoảng ngày khác nhau giao nhau.

Cần khóa việc kiểm tra và ghi trong cùng cơ chế giao dịch phù hợp SQLite; nếu chọn MySQL cần thử đồng thời trên MySQL thật. Không chỉ sửa giao diện hoặc bắt lỗi unique. Tiêu chí nghiệm thu: một yêu cầu thành công, yêu cầu chồng lịch còn lại bị từ chối rõ ràng, không tạo hai booking.

**B. SQLite chưa thực thi khóa ngoại.**

Nguồn: `core/database.py:18`, `backend/services/booking_service.py:24`, `backend/services/rooms_service.py:125`.

Đặt phòng với `customer_id=999999` trả 200. Xóa phòng đã có booking trả 200 và tạo một vi phạm `PRAGMA foreign_key_check`. Cần bật `PRAGMA foreign_keys=ON` cho từng kết nối; kiểm tra tồn tại khóa tham chiếu và chặn xóa lịch sử ở service; rollback và trả lỗi nghiệp vụ thay cho 500. Dữ liệu thật hiện chưa có vi phạm, nhưng hệ thống có thể tạo ra vi phạm.

**C. AI thật chưa hoàn tất được đầu ra trong lần kiểm tra.**

Nguồn: `backend/services/ai_service.py:26`, `backend/services/ai_service.py:39`.

Cả ba service phát sinh lỗi 503 dù danh sách model đã có. Kiểm tra trực tiếp hai endpoint suy luận gặp timeout. Cần xem log Ollama, tài nguyên và thời gian tải/sinh model; đo thời gian thực, giới hạn đầu ra và điều chỉnh timeout có căn cứ. Có cảnh báo rõ khi AI lỗi là điểm tốt, nhưng test mock không thay cho bằng chứng model hoạt động.

**D. Khóa JWT đang dùng giá trị mẫu.**

Nguồn: `core/config.py:12`, cấu hình local hiện tại.

Đã kiểm tra bằng phép so sánh boolean, không ghi giá trị secret vào báo cáo. Cần sinh khóa ngẫu nhiên riêng và từ chối cấu hình mẫu khi chạy môi trường triển khai. Thêm luồng đổi mật khẩu để thực hiện được khuyến cáo trong README; quản lý seed tài khoản demo theo môi trường.

### P1 — Sửa để nghiệp vụ và kết quả AI đúng

| Vấn đề | Kết quả tái hiện / căn cứ | Hướng sửa và nghiệm thu |
|---|---|---|
| Không đặt lại được đúng lịch đã hủy | Hủy booking rồi đặt cùng phòng/cùng ngày → HTTP 500. `entities.py:78` unique không xét trạng thái; service chỉ xét lịch còn hiệu lực. | Điều chỉnh ràng buộc sau khi đã có cơ chế chống chồng lịch đúng; rollback/bắt lỗi. Đặt lại sau hủy phải thành công. |
| Hủy lịch tương lai đổi sai phòng đang có khách | Booking A checked-in, booking B cùng phòng ở khoảng sau; hủy B → phòng từ `occupied` thành `available`. `booking_service.py:44`. | Hủy reservation không tự giải phóng tình trạng vật lý hiện tại; xét lưu trú đang hoạt động trong transaction. |
| Nhận phòng bảo trì vẫn thành công | Tạo booking, chuyển phòng maintenance, check-in → 200 và occupied. `booking_service.py:44`. | Kiểm tra lại phòng, lịch, khách đang ở và quy tắc ngày khi check-in; có chính sách rõ cho nhận sớm/trả muộn. |
| Không chốt giá phòng theo booking | Đặt giá 900.000/đêm, thay giá loại phòng thành 1.200.000 rồi tính 2 đêm → 2.400.000. `invoice_service.py:12`. | Lưu đơn giá tại thời điểm xác nhận và dùng đơn giá đó trên hóa đơn; đổi giá niêm yết không tự đổi giá đã chốt. |
| Trả phòng xóa giảm giá đã lập | Lập hóa đơn giảm 100.000 rồi check-out → discount=0. `booking_service.py:59`, `invoice_service.py:8`. | Phân biệt tính lần đầu/tính lại; bảo toàn giảm giá đã xác nhận, kiểm tra tổng và tiền đã thu. |
| Booking hủy vẫn lập hóa đơn và thu tiền như lưu trú thường | Calculate và payment đều trả 200 sau cancel. `invoice_service.py:40`. | Chặn luồng này hoặc xây chính sách phí hủy/đặt cọc/hoàn tiền riêng, minh bạch. Đề không bắt buộc thêm toàn bộ module hoàn tiền. |
| Tư vấn AI nhận ngày đảo ngược | Check-out trước check-in vẫn 200 và gọi model. `inputs.py:76`. | Dùng validation khoảng ngày tương tự BookingIn và test 422 trước khi gọi AI. |
| AI có thể trả phòng ngoài danh sách | Mock model trả “phòng 9999”; hệ thống chuyển nguyên văn cho frontend. `ai_service.py:133`. | Dùng đầu ra có cấu trúc, kiểm chứng room ID thuộc danh sách đã lọc, số lựa chọn tối đa 3; từ chối hoặc sinh lại có giới hạn khi sai. Đồng bộ phòng trong văn bản với trường `rooms`. |
| Chat có thể chuyển dữ liệu nhạy cảm do nhân viên nhập | Chuỗi giấy tờ giả được giữ nguyên trong payload gửi hàm model. `ai_service.py:114`. | Chặn/che dữ liệu nhạy cảm trước khi gửi, giới hạn trường hợp đầu vào tự do; thêm test bằng dữ liệu giả. Prompt bảo model không tiết lộ không ngăn dữ liệu đã bị gửi. |
| Dashboard tính cả phòng dọn/bảo trì vào công suất | Một phòng cleaning, không có occupied → dashboard 100%. `page_service.py:7`. | Ghi rõ “không sẵn sàng” nếu đó là chủ đích; tách công suất lưu trú, tỷ lệ phòng không bán được và công suất đêm phòng. |
| Doanh thu tháng gắn với ngày xuất hóa đơn | `reports_page_context` cộng `Invoice.paid_amount` theo `issued_at`, không theo `Payment.paid_at`. `page_service.py:63`. | Với chỉ số “tiền thu trong tháng”, cộng Payment theo ngày thu; xử lý rõ dữ liệu lịch sử chưa có payment chi tiết. |
| Chưa lọc loại phòng | Gửi `room_type_id=1` vẫn nhận cả loại 1 và 2. `backend/api/rooms.py:16`. | Khai báo query/filter và thêm bộ lọc ở màn hình đặt phòng. |

Lưu ý: việc thêm khóa duy nhất hoặc kiểm tra ở frontend đơn lẻ không giải quyết lỗi đặt trùng khi đồng thời.

### P2 — Cải thiện chất lượng và mức hoàn thiện

- Xóa phần định nghĩa lặp: `rooms_service.py` có hai bộ hàm; `customers_service.py` và `services_service.py` cũng có các hàm bị khai báo hai lần. Python đang dùng định nghĩa sau, khiến sửa nhầm phần đầu không có tác dụng.
- Bổ sung sửa loại phòng/giá/tiện ích; thêm lịch phòng theo ngày để demo dễ hiểu. Lịch trực quan là cải tiến hữu ích, không được xem như bắt buộc độc lập của đề.
- Đồng bộ giao diện với quyền API: kế toán vẫn thấy một số nút nhận/hủy/sửa; lễ tân thấy nút thu tiền dù API chỉ cho admin/kế toán. Xác định rõ vai trò được đọc giấy tờ và tài chính, sau đó áp dụng cả API và HTML.
- Lịch sử khách nên phân biệt “đã lưu trú”, “đang ở”, “chưa đến” và “đã hủy”.
- Email cần kiểm tra loại email có hợp trạng thái booking không; nhắc thanh toán cần dữ liệu nghiệp vụ đủ dùng, tránh đưa chi tiết tài khoản/thẻ/thông tin thanh toán nhạy cảm vào prompt. Lưu phiên bản prompt/model và kết quả kiểm thử để giải thích khi bảo vệ.
- AI hiện hiển thị bằng `textContent`, giúp tránh thực thi HTML từ model. Nếu cần Markdown như hướng dẫn SDLC thì dùng renderer có vệ sinh nội dung; không thay bằng `innerHTML` trực tiếp.
- Phân trang danh sách và giới hạn dữ liệu chat; hiện chat context lấy toàn bộ phòng và dịch vụ mỗi lượt. Chưa có benchmark nên chưa thể khẳng định đáp ứng tải cụ thể.
- Chuẩn hóa lỗi Pydantic thành câu dễ đọc; helper frontend hiện có thể chuyển mảng lỗi thành `[object Object]`. Chống bấm gửi lặp cho các form ghi dữ liệu và xác định cơ chế chống thu lặp ở backend.
- Chuẩn bị tài nguyên CSS/JS cho demo không có Internet: Bootstrap, icon và Chart.js hiện lấy từ CDN.
- Seed đang tạo phòng occupied/cleaning mà không có booking tương ứng; cần bộ dữ liệu nhất quán, đủ ba vai trò và các trạng thái, có dữ liệu báo cáo qua nhiều tháng.
- Tách chế độ seed demo khỏi khởi động triển khai; thống nhất migration với launcher đang dùng `create_all`. Docker/cloud là điểm cộng, không phải điều kiện bắt buộc trong đề.

## 5. Bộ kiểm thử cần bổ sung

1. Booking: giao nhau một phần, chứa nhau, trùng hoàn toàn, sát biên, sau hủy, hai yêu cầu đồng thời, khách/phòng không tồn tại, vượt sức chứa, ngày sai.
2. Nhận/trả/hủy: mọi chuyển trạng thái hợp lệ và không hợp lệ, phòng bảo trì/dọn/có người, hủy lịch tương lai khi có khách, thao tác lặp.
3. Hóa đơn/thanh toán: nhiều đêm, nhiều dịch vụ, đơn giá đã chốt, giảm giá được giữ, thu một phần/đủ/vượt/âm, thu lặp và thu đồng thời, booking đã hủy, đối chiếu lịch sử.
4. AI tư vấn: hết phòng, ngân sách thấp, yêu cầu mơ hồ, tiện ích không có, ngày sai, model bịa phòng/giá, đầu ra rỗng/sai định dạng/timeout. Chứng minh không tư vấn phòng đã kín.
5. AI email/báo cáo: xác nhận/hủy/nhắc, thông tin đúng trạng thái, không có giấy tờ/chi tiết tài chính cá nhân, số liệu và mốc thời gian đúng. Ghi ít nhất một lần chạy model thật thành công cho từng tính năng.
6. Bảo mật: quyền đọc/ghi theo ba vai trò, token hết hạn/sai/khóa tài khoản, che dữ liệu trước model, khóa mẫu khi triển khai.
7. Triển khai/UX: cài mới, migration từ bản cũ, backup/restore trên bản sao, trình duyệt desktop/mobile, demo khi model hoặc Internet không sẵn sàng.

## 6. Hồ sơ cần chuẩn bị để đáp ứng SDLC và bảo vệ

- Báo cáo: bài toán, phạm vi, quy trình nghiệp vụ, actor/use case, kiến trúc, ERD/từ điển dữ liệu, ràng buộc chống trùng, thiết kế giao diện, API, bảo mật, triển khai và hạn chế.
- Nhật ký AI theo KT1–KT3 và cuối kỳ: prompt thật, kết quả AI, nội dung sinh viên sửa, lý do sửa và kiểm chứng. Không dựng lại lịch sử chưa xảy ra để làm minh chứng.
- Ma trận yêu cầu → màn hình/API → test → kết quả; tách test mock khỏi test model thật.
- Bảng so sánh prompt trước/sau cho phòng/email, đánh giá đúng danh sách phòng, đúng giá/ngày, độ hữu ích và riêng tư; lưu dữ liệu thử giả.
- Hướng dẫn cài đặt đã thử trên môi trường sạch, cấu hình `.env.example`, seed, sao lưu/khôi phục và xử lý lỗi Ollama.
- Slide và kịch bản demo: đăng nhập các vai trò → tạo khách → tìm phòng → AI tư vấn → đặt → thử lịch trùng → sinh email → nhận phòng → thêm dịch vụ → trả phòng → thu một phần/đủ → xem báo cáo → AI khuyến mại → hủy một booking khác và đặt lại.
- Lưu ảnh/video và đầu ra mẫu đã kiểm chứng để hỗ trợ trình bày; đầu ra lưu sẵn cần ghi rõ là minh họa, không thay thế yêu cầu chức năng chạy được.

Thứ tự làm đề xuất: **P0 về tính đúng đắn và AI → P1 nghiệp vụ/riêng tư → test hồi quy và dữ liệu demo → hồ sơ/slide → cải thiện giao diện/đóng gói.** Chưa cần mở rộng chatbot hoặc thêm nghiệp vụ lớn trước khi các lỗi trên được xử lý.
