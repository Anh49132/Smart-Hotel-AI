# Kế hoạch hoàn thiện Lotus Hotel AI — hai người

Ngày lập: 23/10/2026. Phạm vi: phần mềm nội bộ cho quản trị viên, lễ tân, kế toán; bổ sung vai trò buồng phòng với quyền giới hạn. Admin cấp tài khoản nhân viên. Không có đăng ký công khai hoặc cổng khách tự đặt phòng trong đợt này.

## Phương án triển khai đã chốt

- Chạy FastAPI/Jinja2 trên **Render Web Service Free**, dùng chung workspace với dự án khác, nhưng web service, cấu hình và bí mật của khách sạn phải tách riêng.
- Bản online dùng **PostgreSQL Render** trong thời hạn Free hiện có. Kiểm tra database định sử dụng đang chứa dữ liệu dự án nào; không chạy migration khách sạn vào database của dự án khác. Chọn database/logical database khách sạn riêng phù hợp tài nguyên thực có, không tự tạo thêm tài nguyên tính phí.
- PostgreSQL là database nghiệm thu chính. SQLite chỉ dùng local/kiểm thử nhanh; test migration, khóa hàng, đồng thời và tính tiền phải được chạy thêm trên PostgreSQL thật ở database kiểm thử riêng.
- Giữ **Gemini**. `DATABASE_URL`, `GEMINI_API_KEY`, `SECRET_KEY` và mật khẩu bootstrap admin đặt bằng biến môi trường trên service khách sạn; không đưa vào Git, log hoặc browser. Bản online không tạo tài khoản với mật khẩu demo cố định.
- Dự án phục vụ báo cáo, không cần hai web luôn chạy. Để Render tự ngủ khi không sử dụng; không đặt công cụ giữ web thức liên tục. Dùng tên miền `onrender.com` được cấp, chưa mua tên miền hoặc nâng gói.
- Free web ngủ sau 15 phút không truy cập, khởi động lại có độ trễ; các web trong workspace chia sẻ 750 giờ chạy/tháng và hạn mức build/băng thông. PostgreSQL Free hết hạn 30 ngày sau lúc tạo, độc lập với số giờ dùng web. Xác nhận lại trên tài khoản trước triển khai theo [Render Free](https://render.com/docs/free).
- Ghi nhận **ngày hết hạn database thực tế** và **ngày báo cáo** ngay ở bước chuẩn bị. Không mặc định còn 30 ngày tính từ hôm nay. Nếu thời gian triển khai/báo cáo vượt hạn hiện tại, hoàn tất xuất và chuyển dữ liệu trước hạn; Neon Free là phương án tiếp theo đã thống nhất xem xét, không tự chuyển hoặc bật gói trả phí.
- Việc online sớm là bản kiểm thử có tài khoản, dữ liệu giả và migration đã kiểm chứng; chưa gọi đó là bản hoàn thiện trước khi nghiệm thu toàn bộ.

## Điểm xuất phát

Workspace đã có nghiệp vụ cơ bản, migration 0002, lịch sử trạng thái/thanh toán, bản nháp AI và Google Gemini. Lần kiểm tra gần nhất: 41 test đạt; bốn chức năng AI đã gọi thật thành công bằng dữ liệu giả. Đây không phải bằng chứng các lỗi nghiệp vụ trong báo cáo đánh giá đã được sửa.

Hiện còn nhiều thay đổi chưa commit trên main. Trước khi chia việc, kiểm tra và lưu một mốc hiện trạng: `chore: snapshot current hotel system and Gemini integration`. Chỉ stage tệp đã kiểm tra; không đưa .env, database, bản backup, cache hay môi trường ảo vào Git. Ghi tác giả theo người thực hiện/xác nhận mốc hiện trạng. Không phân bổ lại lịch sử cũ thành đóng góp mới.

Mốc hiện trạng và merge commit không nằm trong **26 commit dự kiến: R01/R02 cho PostgreSQL và Render, C01–C24 cho hoàn thiện chức năng**. Giữ ID C01–C24 để dễ đối chiếu kế hoạch trước; R02 được triển khai sau C04. Báo cáo đánh giá trước đó ở `docs/danh-gia-tieu-chi-2026-10-23.md` là danh sách lỗi đầu vào.

## Phân công và Git

- **A:** Anh49132 — `anh49132@gmail.com`.
- **B:** `khanhhoang1012006@gmail.com`; sử dụng tên hiển thị thực tế của người này khi cấu hình Git.
- Mỗi người có **13 commit: 12 commit chức năng và 1 commit hạ tầng**, phụ trách cả phần backend, giao diện, migration và test cần thiết của phần mình. Số commit là cách chia công việc dự kiến, không phải thước đo duy nhất của đóng góp; sau mỗi đợt cần cân lại khối lượng thực tế.
- Mỗi dòng là một nhánh/PR và một commit nghiệp vụ chính. Nếu phát sinh sửa lỗi đáng kể, giữ commit sửa bổ sung có nội dung rõ ràng, không ép lịch sử để giữ đúng con số.
- Nhánh do A thực hiện: **B review và merge**. Nhánh do B thực hiện: **A review và merge**. Như vậy mỗi người review/merge 13 PR nếu giữ đúng cấu trúc kế hoạch.
- Dùng merge commit để giữ tác giả các commit và thấy rõ điểm tích hợp. Trên GitHub, tài khoản bấm merge quyết định người thực hiện merge; đổi user.email trong Git không đổi đăng nhập GitHub.
- Tạo nhánh từ main mới nhất sau khi các phụ thuộc đã merge. Hai người có thể làm song song các việc độc lập ở checkout/worktree riêng. Không đổi nhánh của cùng một thư mục khi người kia còn đang sửa.
- Nếu dùng chung máy, dùng cấu hình `git -c user.name=... -c user.email=... commit ...` cho từng lần commit; kiểm tra `git var GIT_AUTHOR_IDENT` trước đó. Email phải thuộc tài khoản tương ứng để liên kết tác giả đúng.
- Migrations phải có thứ tự revision nhất quán; trước khi merge, đối chiếu head mới và chỉnh phụ thuộc migration nếu hai nhánh cùng thêm schema.
- Cập nhật main qua PR, tránh push trực tiếp lên nhánh đang chạy online. Auto-deploy chỉ được bật sau khi xác định đúng service khách sạn và có CI phù hợp; mọi migration phải tương thích dữ liệu và có bản sao trước thay đổi quan trọng. Khôi phục mã không tự khôi phục database.

## Đợt hạ tầng — PostgreSQL trước, online sau khi sửa lỗi nền tảng

| ID | Người | Nhánh | Commit message | Kết quả và nghiệm thu |
|---|---|---|---|---|
| R01 | A | `feature/r01-postgres` | `feat(db): support PostgreSQL and verified SQLite data transfer` | Thêm driver PostgreSQL, chuẩn hóa URL `postgres://`/`postgresql://`, pool giới hạn và TLS cho kết nối ngoài Render. Kiểm chứng migrations 0001/0002 với các enum dùng chung trên PostgreSQL, nâng cấp được DB mới và DB cũ phù hợp. Công cụ chuyển SQLite đọc nguồn, nhập theo thứ tự FK vào đích riêng/rỗng, giữ ID/hash mật khẩu/Decimal/ngày/trạng thái, đồng bộ sequence, đối chiếu số dòng và tổng tiền. Không ghi đè DB có dữ liệu; không đổi cấu hình local trước khi đối chiếu đạt. |
| R02 | B | `feature/r02-render-demo` | `chore(render): deploy isolated hotel demo with secure runtime configuration` | Sau C04: cấu hình build/start, Python tương thích, bind `0.0.0.0:$PORT`, migration trước app theo khả năng Free, health check nhanh không gọi Gemini. Tách service/database và secret khỏi dự án khác; bootstrap admin bằng mật khẩu riêng, cookie HTTPS và cấu hình môi trường. Ưu tiên tái sử dụng đúng tài nguyên người dùng xác nhận, không tạo trùng. Chỉ cấu hình Blueprint nếu phù hợp cơ chế quản lý tài nguyên; kiểm tra trước khi sync. Xác nhận deploy live, login/phân quyền/CRUD/lưu dữ liệu sau redeploy và một lượt AI bằng dữ liệu giả. Ghi URL và hạn database vào tài liệu vận hành. |

Thứ tự đầu dự án: **chốt hiện trạng → R01 → C01 → C02 → C03 → C04 → R02**. C04 có thể phát triển song song các phần độc lập, nhưng chỉ online sau khi sửa lỗi dữ liệu, quyền và tài khoản mặc định. Sau R02, kiểm tra bản online ở cuối mỗi đợt thay vì đợi đến cuối kỳ.

## Đợt 1 — Sửa nền tảng dữ liệu, đặt phòng và tài khoản

| ID | Người | Nhánh | Commit message | Kết quả và nghiệm thu |
|---|---|---|---|---|
| C01 | A | `feature/c01-db-integrity` | `fix(db): enforce references and remove duplicate services` | Kiểm tra toàn vẹn PostgreSQL và bật FK cho kết nối SQLite local; kiểm tra ID tham chiếu; chặn xóa dữ liệu đang có lịch sử; chuẩn hóa rollback/lỗi và bỏ các định nghĩa service trùng. Dữ liệu cũ phải được kiểm tra trước khi áp ràng buộc. Test ID không tồn tại, xóa phòng đã đặt, migration trên bản sao. |
| C02 | B | `feature/c02-booking-consistency` | `fix(bookings): prevent concurrent overlaps and invalid transitions` | Transaction/khóa hàng phù hợp PostgreSQL; sửa đặt lại sau hủy, hủy lịch tương lai và nhận phòng bảo trì/dọn/có người. Khóa kiểm tra và ghi cùng phạm vi, không chỉ bắt unique. Test hai session PostgreSQL đồng thời với hai khoảng giao nhau: chỉ một thành công; sát biên vẫn hợp lệ. Nếu vẫn hỗ trợ SQLite local, phải có cơ chế và test riêng cho SQLite, không dựa vào FOR UPDATE. |
| C03 | A | `feature/c03-invoice-correctness` | `fix(invoices): preserve booked rates and financial adjustments` | Snapshot giá theo booking; giữ giảm giá khi checkout; chặn lập hóa đơn lưu trú thường cho booking hủy; ràng buộc số tiền. Giá cũ được backfill có ghi rõ giới hạn truy hồi. Test đổi giá niêm yết, trả nhiều đêm/dịch vụ, giảm giá và thanh toán. |
| C04 | B | `feature/c04-staff-security` | `feat(auth): secure staff accounts and password changes` | Admin tạo/cấp quyền/khóa tài khoản; đổi mật khẩu và đặt lại mật khẩu qua admin; thu hồi phiên cũ sau đổi/reset/khóa. Chặn khóa mẫu ở chế độ triển khai; cookie theo môi trường, giới hạn thử đăng nhập, UI theo quyền. Test ba vai trò, tài khoản khóa, token cũ. |

Phụ thuộc: C01 → C02 → C03. C04 có thể làm song song C01, tích hợp schema lần lượt. Chốt đợt bằng việc chạy lại các tình huống lỗi đã tái hiện trong báo cáo.

## Đợt 2 — Hoàn thiện đặt phòng và giá

| ID | Người | Nhánh | Commit message | Kết quả và nghiệm thu |
|---|---|---|---|---|
| C05 | A | `feature/c05-room-rates` | `feat(rates): manage room types and dated rate plans` | CRUD hợp lý cho loại phòng/tiện ích/sức chứa, ngừng bán thay cho xóa lịch sử; giá thường/cuối tuần/ngày đặc biệt và quy tắc ưu tiên. Booking lưu chi tiết đơn giá theo từng đêm; thay bảng giá không đổi giá đã chốt. Test đêm qua cuối tuần, khoảng ngày đặc biệt và quy tắc trùng. |
| C06 | B | `feature/c06-booking-detail` | `feat(bookings): add unified reservation detail and timeline` | Một màn hình khách, ngày ở, phòng, giá, dịch vụ, tiền và lịch sử; nút theo trạng thái/quyền; có trạng thái rỗng và lỗi rõ. Tái sử dụng API lịch sử hiện có. Test quyền và render có/không có hóa đơn, dịch vụ. |
| C07 | A | `feature/c07-booking-changes` | `feat(bookings): support date changes extensions and room moves` | Sửa lịch, gia hạn, đổi phòng trước khi đến và khi đang ở. Lưu các chặng phân phòng để giữ lịch sử phòng/đêm và giá từng chặng. Thay đổi giao dịch nguyên tử, kiểm tra trùng lại, ghi lý do/người đổi. Test đổi thất bại rollback, đổi giữa kỳ và chênh lệch giá. |
| C08 | B | `feature/c08-room-calendar` | `feat(calendar): add room timeline and availability filters` | Lịch hàng=phòng/cột=ngày; nhấn để đặt/xem chi tiết; bộ lọc ngày, loại, tầng, số khách; biểu thị đặt phòng và các chặng đổi phòng. Backend hỗ trợ filter thật. Test dữ liệu lịch, sát biên và thao tác browser desktop/mobile. |

Phụ thuộc: C05 sau C03; C06 sau đợt 1; C07 sau C05; C08 hoàn tất sau C06/C07. Calendar ưu tiên thao tác nhấn; kéo thả chỉ bổ sung khi có thời gian và kiểm tra xung đột tương đương backend.

## Đợt 3 — Buồng phòng, bảo trì, lễ tân và khách hàng

| ID | Người | Nhánh | Commit message | Kết quả và nghiệm thu |
|---|---|---|---|---|
| C09 | A | `feature/c09-housekeeping` | `feat(housekeeping): assign cleaning tasks and verify readiness` | Vai trò buồng phòng chỉ xem thông tin cần thiết; quy trình cần dọn → đang dọn → chờ kiểm tra → sẵn sàng; phân công, thời điểm hoàn thành. Checkout/đổi phòng tạo việc phù hợp. Test lễ tân chỉ nhận khách khi đủ điều kiện, quyền nhân viên dọn. |
| C10 | B | `feature/c10-maintenance` | `feat(maintenance): schedule room blocks and track repairs` | Phiếu sự cố, người xử lý, khóa bán theo khoảng ngày; không âm thầm ghi đè booking có sẵn, phải báo xung đột để nhân viên xử lý. Bộ lọc phòng trống, lịch và AI dùng chung quy tắc block. Test hết thời hạn block và khoảng ngày chồng booking. |
| C11 | A | `feature/c11-frontdesk` | `feat(frontdesk): add arrivals departures and no-show workflow` | Bảng khách đến/đi/đang ở, quá giờ và công nợ; xử lý walk-in bằng luồng đặt rồi nhận; no-show là trạng thái riêng. Cấu hình giờ nhận/trả và phụ thu, nhân viên xác nhận trước áp dụng. Test ngày/giờ tại Asia/Bangkok, trạng thái và phụ thu. |
| C12 | B | `feature/c12-guest-history` | `feat(customers): add accurate stay history and guest notes` | Chi tiết lịch sử đã ở/đang ở/chưa đến/hủy/no-show; tìm kiếm/phân trang; ghi chú sở thích; che giấy tờ và quyền xem phù hợp. Test đếm đúng lượt lưu trú và không lộ dữ liệu trong API/HTML ngoài quyền. |

Phụ thuộc: C09 sau C04/C07; C10 sau C08; C11 sau C09/C10; C12 sau C07 và tích hợp no-show từ C11. Giữ riêng trạng thái reservation, tình trạng vật lý phòng và block theo lịch.

## Đợt 4 — Tài chính và bàn giao ca

| ID | Người | Nhánh | Commit message | Kết quả và nghiệm thu |
|---|---|---|---|---|
| C13 | A | `feature/c13-deposits` | `feat(payments): record deposits and reconcile reservation balances` | Thu cọc trước nhận phòng; số tiền/phương thức/người thu/mã tham chiếu; tính số dư chính xác và đối trừ khi thanh toán. Có khóa/chống lặp và kiểm soát đồng thời cho giao dịch tiền. Không lưu thông tin thẻ. Test thu một phần/đủ/lặp/đồng thời. |
| C14 | B | `feature/c14-folio` | `feat(invoices): add itemized folios receipts and printing` | Hiển thị tiền từng đêm/chặng phòng, dịch vụ, phụ thu, giảm giá, cọc, thanh toán và số dư. Phiếu thu/hóa đơn in từng booking; phân biệt chứng từ nội bộ với hóa đơn điện tử. Test tổng chi tiết bằng tổng sổ giao dịch; xem bản in thực. |
| C15 | A | `feature/c15-refunds` | `feat(finance): add authorized refunds and cancellation adjustments` | Chính sách phí hủy/hoàn cọc cơ bản, thao tác có quyền và lý do; bổ sung giao dịch điều chỉnh/hoàn, không xóa giao dịch cũ. Refund trong phạm vi tiền đã thu; tương thích no-show. Test quyền, hoàn một phần, lặp/đồng thời và đối soát số dư. |
| C16 | B | `feature/c16-shift-handover` | `feat(shifts): reconcile cashier shifts and handover notes` | Mở/đóng ca, tiền đầu ca, thu/hoàn theo phương thức, tiền mặt kỳ vọng/thực đếm/chênh lệch, người bàn giao/nhận và việc tồn. Giao dịch mới gắn ca đang mở; ca đóng không bị sửa âm thầm. Test tổng theo giao dịch, quyền và chốt ca. |

Phụ thuộc: C13 sau C03/C07; C14/C15 sau C13; C16 sau C15. Khoản thu và lịch sử Payment cũ phải có kế hoạch chuyển tiếp/đối chiếu để không đếm hai lần. Bản đầu chỉ ghi nhận thu tiền/chuyển khoản do nhân viên xác nhận, không tích hợp cổng thanh toán tự động.

## Đợt 5 — Báo cáo, Gemini và kiểm soát AI

| ID | Người | Nhánh | Commit message | Kết quả và nghiệm thu |
|---|---|---|---|---|
| C17 | A | `feature/c17-operating-reports` | `feat(reports): reconcile occupancy revenue cashflow and receivables` | Chọn khoảng ngày; thống kê lượt đặt, công suất đêm phòng, doanh thu hóa đơn, tiền thu theo ngày giao dịch, cọc/công nợ và hoàn tiền. Công bố công thức, quy tắc phòng bảo trì và mốc thời gian; xuất CSV không lộ giấy tờ. Test qua tháng/đổi phòng/hoàn tiền/bảo trì. |
| C18 | B | `feature/c18-room-advice` | `feat(ai): validate structured room recommendations against availability` | Giữ Gemini hiện có; dùng kết quả có cấu trúc và kiểm chứng ID/giá/phòng còn trống từ một nguồn truy vấn chung. Xét ngày, sức chứa, ngân sách, tiện ích, block bảo trì; tối đa ba lựa chọn. Test hết phòng, ngày sai, ngân sách thấp, prompt injection, model bịa phòng/giá. |
| C19 | A | `feature/c19-booking-emails` | `feat(ai): generate contextual booking emails with review history` | Hoàn thiện email xác nhận/hủy/thay đổi lịch/nhắc thanh toán theo trạng thái; dữ liệu tối thiểu, không giấy tờ/tài khoản/thẻ. Lưu loại email, model, phiên bản prompt và kết quả duyệt; soạn/sao chép/in bản nháp. Test từng loại và dữ liệu nhạy cảm bằng dữ liệu giả. |
| C20 | B | `feature/c20-ai-reports` | `feat(ai): ground reports and handovers in verified metrics` | Gemini giải thích số liệu C17 và gợi ý khuyến mại; tóm tắt ca ở phạm vi quyền. Mở rộng kiểm tra riêng tư chat, giới hạn ngữ cảnh, request và xử lý lỗi. Test không bịa số liệu, không vượt quyền; lưu đánh giá prompt và chạy thật mẫu nhỏ theo quota. |

Phụ thuộc: C17 sau đợt 4; C18 sau C08/C10; C19 sau C07/C15; C20 sau C16/C17/C18. Tính tiền, quyết định phòng trống và phân quyền do code/DB thực hiện; AI chỉ diễn giải hoặc đề xuất, không tự ghi nghiệp vụ. Không cam kết riêng việc đổi model giải quyết lỗi sai đầu ra.

## Đợt 6 — Nghiệm thu, dữ liệu demo, triển khai và bảo vệ

| ID | Người | Nhánh | Commit message | Kết quả và nghiệm thu |
|---|---|---|---|---|
| C21 | A | `feature/c21-release-tests` | `test(system): verify end-to-end stays security and concurrency` | Bộ kiểm thử tích hợp toàn luồng và hồi quy các lỗi ban đầu; kiểm thử đồng thời đặt/đổi/thu/hoàn tiền và ma trận quyền trên PostgreSQL kiểm thử riêng. Đo tải dữ liệu demo, phân biệt cold start Render với thời gian xử lý khi web đã thức; ghi môi trường/kết quả thực, không suy đoán khả năng chịu tải. |
| C22 | B | `feature/c22-demo-and-ux` | `feat(demo): add consistent seed data and complete operational UX` | Seed tái chạy an toàn, có đủ vai trò/trạng thái, lịch nhiều tháng, cọc/hoàn/ca; dữ liệu giả. Hoàn thiện responsive, lỗi dễ đọc, loading/chống bấm lặp, phân trang, tài nguyên giao diện sẵn cho demo. Kiểm thử browser desktop/mobile và bản in. |
| C23 | A | `feature/c23-deployment` | `chore(deploy): package app and verify PostgreSQL backup restore` | Hoàn thiện bản Render đã lên ở R02; Docker để tái lập/local dự phòng, CI và hướng dẫn triển khai. Bản bàn giao dùng PostgreSQL: cài mới/nâng cấp bản sao DB, pg_dump và restore vào DB kiểm thử có đối chiếu số dòng/tổng tiền/sequence; kiểm chứng đường quay lại bản mã trước tương thích schema. Chuẩn bị hướng dẫn chuyển PostgreSQL Render sang Neon qua DATABASE_URL và dump/restore; chỉ thực hiện chuyển đích khi được chọn và trước hạn DB. Secret vẫn ở môi trường, không có dữ liệu thật trong Git. |
| C24 | B | `feature/c24-defense-docs` | `docs(project): complete technical report AI evidence and demo slides` | README, actor/use case, ERD/từ điển dữ liệu, kiến trúc, wireframe, ma trận yêu cầu-test, mô tả AI/giới hạn và log SDLC thật. Slide, kịch bản demo và câu hỏi bảo vệ; A rà soát kỹ thuật và cùng diễn tập. Log AI được thu từ đầu từng commit, không dựng lại lịch sử. |

Phụ thuộc: C21 tích hợp sau C20; C22 chuẩn bị dữ liệu từ trước và hoàn tất sau C21; C23 sau C21/C22; C24 cập nhật liên tục và chốt sau C23. Đây là test tích hợp/nghiệm thu cuối, không thay cho test phải có ngay trong từng commit chức năng.

## Điều kiện merge cho mọi PR

1. Đáp ứng kết quả nghiệm thu của dòng công việc; migration/backfill được xem xét nếu đổi dữ liệu.
2. Test liên quan và bộ hồi quy đang có đạt; không để PR không liên quan sửa/hủy dữ liệu để vượt test.
3. Có phản hồi lỗi dễ hiểu và backend kiểm tra quyền/quy tắc, không chỉ kiểm tra ở giao diện.
4. Không có key, giấy tờ thật hoặc database trong diff; không gửi dữ liệu thật để thử AI.
5. README/tài liệu API/nhật ký AI được cập nhật khi cần; PR ghi rõ vấn đề, hành vi mới và bằng chứng kiểm tra.
6. Người còn lại review rồi merge bằng tài khoản của mình. Tác giả xử lý phản hồi trước khi merge.

## Liên kết với tiêu chí học phần

| Tiêu chí | Minh chứng chính |
|---|---|
| 1. Chức năng đầy đủ/ổn định | C01–C20, luồng tích hợp C21 |
| 2. Kiến trúc/mã nguồn | C01, module hóa xuyên các PR, review chéo |
| 3. CSDL | R01, C01–C03, các migration, C22/C23 |
| 4. UI/UX | C06/C08/C09–C16, C22 và kiểm thử browser |
| 5. AI | C18–C20, prompt và kết quả chạy thật có đánh giá |
| 6. Bảo mật/riêng tư | C04, C12–C16, C18–C21 và quản lý secret C23 |
| 7. Hiệu năng/ổn định | C02, C13/C15, C20–C23 và số đo thực |
| 8. Triển khai/đóng gói | R02, C22/C23, hướng dẫn C24 và URL demo được kiểm tra |
| 9. Báo cáo kỹ thuật/SDLC | Nhật ký từng PR và C24 |
| 10. Thuyết trình/demo | C22/C24 và diễn tập của cả hai người |

## Mốc nghiệm thu sản phẩm

- **M1:** Sau C04, không tái hiện các lỗi nền tảng đã chặn trong đợt 1.
- **M1-online:** Sau R02, web khách sạn có URL Render, login bằng tài khoản riêng và lưu dữ liệu PostgreSQL qua lần redeploy; kiểm tra dự án khác không bị thay đổi cấu hình. Theo dõi quota và hạn database từ thời điểm này.
- **M2:** Sau C12, lễ tân xử lý đặt/đổi/nhận/trả và phối hợp buồng phòng trên lịch thật.
- **M3:** Sau C16, toàn bộ cọc/thu/hoàn/công nợ/ca đối chiếu được.
- **M4:** Sau C20, AI có đầu ra hữu ích và kiểm soát được, báo cáo có công thức nhất quán.
- **M5:** Sau C24, cài được từ hướng dẫn, có dữ liệu demo, báo cáo/slide/minh chứng và diễn tập hoàn chỉnh.

## Chuẩn bị buổi báo cáo

1. Kiểm tra database chưa hết hạn và quota web/build còn đủ; có bản dump và phương án chạy local dự phòng. Vì kế hoạch 4–6 tuần có thể dài hơn vòng đời database Free đang có, kiểm tra hạn trước mỗi đợt; không đợi C23 mới xuất dữ liệu nếu database sắp hết hạn.
2. Mở web trước 5–10 phút để qua cold start; kiểm tra đăng nhập, phòng trống, đặt phòng và Gemini. Không chạy liên tục để giữ web thức trong các ngày không demo.
3. Dùng dữ liệu giả đủ tình huống; chuẩn bị tài khoản riêng cho từng vai trò, hóa đơn mẫu và bộ câu hỏi AI đã thử.
4. Demo chính: lịch phòng → tìm phòng/AI tư vấn → tạo booking và email → thu cọc → nhận phòng → dịch vụ → đổi phòng/gia hạn → checkout → đối trừ/thu đủ → buồng phòng → báo cáo/AI → bàn giao ca.
5. Demo ngoại lệ: hai lịch giao nhau bị chặn, hủy rồi đặt lại, nhận phòng bảo trì bị chặn, sai quyền bị từ chối, AI lỗi có thông báo và nghiệp vụ quản lý vẫn dùng được.
6. Mang báo cáo/slide, ma trận yêu cầu-test, link repository/PR và nhật ký AI thật. Cả hai người diễn tập phần mình làm và phần review.

Ước lượng ban đầu: 4–6 tuần với hai người làm đều; cần hiệu chỉnh sau đợt 1 theo thời gian thực. Đổi phòng giữa kỳ, giao dịch tiền và migration là những hạng mục cần dự phòng. Mốc online không phụ thuộc việc hoàn tất toàn bộ 26 commit, nhưng phụ thuộc sửa lỗi nền tảng và bảo mật trước. Không xác nhận “đủ 10 tiêu chí” chỉ dựa vào số commit: chỉ xác nhận sau nghiệm thu và kiểm tra tài liệu/demo.
