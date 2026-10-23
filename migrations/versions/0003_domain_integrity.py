"""Validate legacy rows before enforcing basic domain constraints."""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"
branch_labels = depends_on = None

CONSTRAINTS = {
    "room_types": [("ck_room_type_capacity", "capacity > 0"), ("ck_room_type_rate", "nightly_rate > 0")],
    "bookings": [("ck_booking_dates", "check_out > check_in"), ("ck_booking_guests", "guests > 0")],
    "services": [("ck_service_price", "price > 0")],
    "service_usages": [("ck_usage_quantity", "quantity > 0"), ("ck_usage_price", "unit_price >= 0")],
}


def upgrade():
    bind = op.get_bind()
    for table, constraints in CONSTRAINTS.items():
        for name, expression in constraints:
            if bind.scalar(sa.text(f"SELECT COUNT(*) FROM {table} WHERE NOT ({expression})")):
                raise RuntimeError(f"Legacy data violates {name}; repair a backup copy before upgrading")
    for table, constraints in CONSTRAINTS.items():
        with op.batch_alter_table(table) as batch:
            for name, expression in constraints:
                batch.create_check_constraint(name, expression)


def downgrade():
    for table, constraints in reversed(list(CONSTRAINTS.items())):
        with op.batch_alter_table(table) as batch:
            for name, _ in constraints:
                batch.drop_constraint(name, type_="check")
