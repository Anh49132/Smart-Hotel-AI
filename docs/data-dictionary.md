# Từ điển dữ liệu

Sinh từ SQLAlchemy metadata của bản bàn giao; không đọc dữ liệu khách.

## customers

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| full_name | VARCHAR(120) | False |  |
| phone | VARCHAR(30) | False |  |
| email | VARCHAR(160) | True |  |
| identity_number | VARCHAR(80) | True |  |
| preference_notes | TEXT | False |  |

Ràng buộc: PrimaryKeyConstraint.

## demo_seeds

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| name | VARCHAR(60) | False | PK;  |
| anchor_date | DATE | False |  |
| created_at | DATETIME | False |  |

Ràng buộc: PrimaryKeyConstraint.

## hotel_policy

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| check_in_hour | INTEGER | False |  |
| check_out_hour | INTEGER | False |  |
| no_show_hour | INTEGER | False |  |
| early_fee | NUMERIC(12, 2) | False |  |
| late_fee | NUMERIC(12, 2) | False |  |
| cancellation_percent | NUMERIC(5, 2) | False |  |
| no_show_percent | NUMERIC(5, 2) | False |  |

Ràng buộc: PrimaryKeyConstraint; ck_policy_hours: check_in_hour BETWEEN 0 AND 23 AND check_out_hour BETWEEN 0 AND 23 AND no_show_hour BETWEEN 0 AND 23; ck_policy_cancellation: cancellation_percent BETWEEN 0 AND 100 AND no_show_percent BETWEEN 0 AND 100; ck_policy_singleton: id=1; ck_policy_fees: early_fee >= 0 AND late_fee >= 0.

## room_types

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| name | VARCHAR(80) | False |  |
| capacity | INTEGER | False |  |
| nightly_rate | NUMERIC(12, 2) | False |  |
| weekend_rate | NUMERIC(12, 2) | True |  |
| is_active | BOOLEAN | False |  |
| amenities | TEXT | False |  |

Ràng buộc: ck_room_type_weekend: weekend_rate IS NULL OR weekend_rate > 0; UniqueConstraint; ck_room_type_rate: nightly_rate > 0; ck_room_type_capacity: capacity > 0; PrimaryKeyConstraint.

## services

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| name | VARCHAR(100) | False |  |
| unit | VARCHAR(30) | False |  |
| price | NUMERIC(12, 2) | False |  |
| active | BOOLEAN | False |  |

Ràng buộc: PrimaryKeyConstraint; UniqueConstraint; ck_service_price: price > 0.

## users

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| username | VARCHAR(50) | False |  |
| full_name | VARCHAR(120) | False |  |
| password_hash | VARCHAR(255) | False |  |
| role | VARCHAR(12) | False |  |
| is_active | BOOLEAN | False |  |
| token_version | INTEGER | False |  |
| must_change_password | BOOLEAN | False |  |

Ràng buộc: PrimaryKeyConstraint.

## cashier_shifts

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| cashier_id | INTEGER | False | users.id |
| status | VARCHAR(10) | False |  |
| opened_at | DATETIME | False |  |
| closed_at | DATETIME | True |  |
| opening_cash | NUMERIC(12, 2) | False |  |
| counted_cash | NUMERIC(12, 2) | True |  |
| expected_cash | NUMERIC(14, 2) | True |  |
| difference | NUMERIC(14, 2) | True |  |
| handed_to | INTEGER | True | users.id |
| note | VARCHAR(2000) | False |  |
| snapshot_json | TEXT | False |  |

Ràng buộc: ForeignKeyConstraint; ForeignKeyConstraint; ck_shift_status: status IN ('open','closed'); PrimaryKeyConstraint; ck_shift_amounts: opening_cash >= 0 AND (counted_cash IS NULL OR counted_cash >= 0).

## rate_plans

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| room_type_id | INTEGER | False | room_types.id |
| name | VARCHAR(100) | False |  |
| start_date | DATE | False |  |
| end_date | DATE | False |  |
| nightly_rate | NUMERIC(12, 2) | False |  |
| is_active | BOOLEAN | False |  |

Ràng buộc: ForeignKeyConstraint; PrimaryKeyConstraint; ck_rate_plan_dates: end_date > start_date; ck_rate_plan_price: nightly_rate > 0.

## rooms

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| number | VARCHAR(20) | False |  |
| floor | INTEGER | False |  |
| status | VARCHAR(11) | False |  |
| room_type_id | INTEGER | False | room_types.id |

Ràng buộc: PrimaryKeyConstraint; ForeignKeyConstraint.

## bookings

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| code | VARCHAR(24) | False |  |
| customer_id | INTEGER | False | customers.id |
| room_id | INTEGER | False | rooms.id |
| check_in | DATE | False |  |
| check_out | DATE | False |  |
| guests | INTEGER | False |  |
| booked_nightly_rate | NUMERIC(12, 2) | False |  |
| booked_rate_source | VARCHAR(24) | False |  |
| status | VARCHAR(11) | False |  |
| note | TEXT | False |  |
| created_at | DATETIME | False |  |
| actual_check_in | DATETIME | True |  |
| actual_check_out | DATETIME | True |  |

Ràng buộc: ck_booking_guests: guests > 0; PrimaryKeyConstraint; ck_booking_rate: booked_nightly_rate >= 0; ck_booking_dates: check_out > check_in; ForeignKeyConstraint; ForeignKeyConstraint.

## cleaning_tasks

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| room_id | INTEGER | False | rooms.id |
| assigned_to | INTEGER | True | users.id |
| status | VARCHAR(20) | False |  |
| created_at | DATETIME | False |  |
| started_at | DATETIME | True |  |
| completed_at | DATETIME | True |  |
| inspected_at | DATETIME | True |  |
| inspected_by | INTEGER | True | users.id |

Ràng buộc: ck_cleaning_status: status IN ('pending','in_progress','inspection','ready'); ForeignKeyConstraint; ForeignKeyConstraint; ForeignKeyConstraint; PrimaryKeyConstraint.

## room_blocks

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| room_id | INTEGER | False | rooms.id |
| start_date | DATE | False |  |
| end_date | DATE | False |  |
| description | VARCHAR(500) | False |  |
| status | VARCHAR(20) | False |  |
| assigned_to | INTEGER | True | users.id |
| created_by | INTEGER | False | users.id |
| created_at | DATETIME | False |  |
| resolved_at | DATETIME | True |  |

Ràng buộc: ForeignKeyConstraint; ck_block_dates: end_date > start_date; ForeignKeyConstraint; ck_block_status: status IN ('open','in_progress','resolved','cancelled'); ForeignKeyConstraint; PrimaryKeyConstraint.

## ai_results

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| kind | VARCHAR(30) | False |  |
| content | TEXT | False |  |
| email_kind | VARCHAR(30) | False |  |
| model_name | VARCHAR(80) | False |  |
| prompt_version | VARCHAR(40) | False |  |
| source_json | TEXT | False |  |
| booking_id | INTEGER | True | bookings.id |
| review_status | VARCHAR(20) | False |  |
| generated_by | INTEGER | False | users.id |
| reviewed_by | INTEGER | True | users.id |
| created_at | DATETIME | False |  |
| reviewed_at | DATETIME | True |  |

Ràng buộc: ForeignKeyConstraint; PrimaryKeyConstraint; ForeignKeyConstraint; ForeignKeyConstraint.

## booking_changes

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| booking_id | INTEGER | False | bookings.id |
| changed_by | INTEGER | True | users.id |
| reason | VARCHAR(500) | False |  |
| before_data | TEXT | False |  |
| after_data | TEXT | False |  |
| changed_at | DATETIME | False |  |

Ràng buộc: ForeignKeyConstraint; PrimaryKeyConstraint; ForeignKeyConstraint.

## booking_nights

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| booking_id | INTEGER | False | bookings.id |
| stay_date | DATE | False |  |
| amount | NUMERIC(12, 2) | False |  |
| source | VARCHAR(120) | False |  |

Ràng buộc: ck_booking_night_amount: amount >= 0; PrimaryKeyConstraint; ForeignKeyConstraint; uq_booking_night.

## booking_status_history

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| booking_id | INTEGER | False | bookings.id |
| from_status | VARCHAR(11) | True |  |
| to_status | VARCHAR(11) | False |  |
| changed_by | INTEGER | True | users.id |
| changed_at | DATETIME | False |  |

Ràng buộc: PrimaryKeyConstraint; ForeignKeyConstraint; ForeignKeyConstraint.

## booking_surcharges

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| booking_id | INTEGER | False | bookings.id |
| kind | VARCHAR(10) | False |  |
| amount | NUMERIC(12, 2) | False |  |
| confirmed_by | INTEGER | False | users.id |
| confirmed_at | DATETIME | False |  |

Ràng buộc: ck_surcharge_amount: amount > 0; PrimaryKeyConstraint; ForeignKeyConstraint; ck_surcharge_kind: kind IN ('early','late'); uq_booking_surcharge; ForeignKeyConstraint.

## financial_adjustments

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| booking_id | INTEGER | False | bookings.id |
| target_status | VARCHAR(20) | False |  |
| original_total | NUMERIC(12, 2) | False |  |
| fee_amount | NUMERIC(12, 2) | False |  |
| percent | NUMERIC(5, 2) | False |  |
| amount | NUMERIC(12, 2) | False |  |
| reason | VARCHAR(500) | False |  |
| request_key | VARCHAR(64) | False |  |
| actor_id | INTEGER | False | users.id |
| created_at | DATETIME | False |  |

Ràng buộc: ForeignKeyConstraint; PrimaryKeyConstraint; ck_adjustment_status: target_status IN ('cancelled','no_show'); ForeignKeyConstraint; ck_adjustment_math: percent >= 0 AND percent <= 100 AND fee_amount >= 0 AND fee_amount <= original_total AND amount = fee_amount - original_total; UniqueConstraint.

## invoices

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| booking_id | INTEGER | False | bookings.id |
| room_amount | NUMERIC(12, 2) | False |  |
| service_amount | NUMERIC(12, 2) | False |  |
| surcharge_amount | NUMERIC(12, 2) | False |  |
| discount | NUMERIC(12, 2) | False |  |
| total | NUMERIC(12, 2) | False |  |
| paid_amount | NUMERIC(12, 2) | False |  |
| payment_status | VARCHAR(7) | False |  |
| issued_at | DATETIME | False |  |

Ràng buộc: ck_invoice_total: total = room_amount + service_amount + surcharge_amount - discount; PrimaryKeyConstraint; ck_invoice_amounts: room_amount >= 0 AND service_amount >= 0; ck_invoice_surcharge: surcharge_amount >= 0; ForeignKeyConstraint; ck_invoice_discount: discount >= 0 AND discount <= room_amount + service_amount + surcharge_amount; UniqueConstraint; ck_invoice_paid: paid_amount >= 0 AND paid_amount <= total.

## room_stays

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| booking_id | INTEGER | False | bookings.id |
| room_id | INTEGER | False | rooms.id |
| check_in | DATE | False |  |
| check_out | DATE | False |  |

Ràng buộc: ForeignKeyConstraint; ck_stay_dates: check_out > check_in; ForeignKeyConstraint; PrimaryKeyConstraint.

## service_usages

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| booking_id | INTEGER | False | bookings.id |
| service_id | INTEGER | False | services.id |
| quantity | INTEGER | False |  |
| unit_price | NUMERIC(12, 2) | False |  |
| used_at | DATETIME | False |  |

Ràng buộc: ForeignKeyConstraint; ck_usage_quantity: quantity > 0; ForeignKeyConstraint; PrimaryKeyConstraint; ck_usage_price: unit_price >= 0.

## ai_review_events

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| result_id | INTEGER | False | ai_results.id |
| actor_id | INTEGER | False | users.id |
| approved | BOOLEAN | False |  |
| created_at | DATETIME | False |  |

Ràng buộc: ForeignKeyConstraint; PrimaryKeyConstraint; ForeignKeyConstraint.

## payments

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| invoice_id | INTEGER | False | invoices.id |
| amount | NUMERIC(12, 2) | False |  |
| paid_by | INTEGER | True | users.id |
| paid_at | DATETIME | False |  |

Ràng buộc: ForeignKeyConstraint; ck_payments_positive_amount: amount > 0; PrimaryKeyConstraint; ForeignKeyConstraint.

## money_entries

| Cột | Kiểu | Nullable | Khóa/Tham chiếu |
|---|---|---|---|
| id | INTEGER | False | PK;  |
| booking_id | INTEGER | False | bookings.id |
| payment_id | INTEGER | True | payments.id |
| amount | NUMERIC(12, 2) | False |  |
| kind | VARCHAR(20) | False |  |
| method | VARCHAR(20) | False |  |
| reference | VARCHAR(100) | False |  |
| reason | VARCHAR(500) | False |  |
| request_key | VARCHAR(64) | False |  |
| actor_id | INTEGER | True | users.id |
| shift_id | INTEGER | True | cashier_shifts.id |
| occurred_at | DATETIME | False |  |

Ràng buộc: ck_money_positive: amount > 0; ForeignKeyConstraint; ForeignKeyConstraint; ck_money_method: method IN ('cash','bank_transfer','unknown'); uq_money_request; ck_money_kind: kind IN ('deposit','payment','refund','legacy_opening'); ForeignKeyConstraint; PrimaryKeyConstraint; ForeignKeyConstraint; UniqueConstraint.
