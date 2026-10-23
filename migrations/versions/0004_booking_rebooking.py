"""Allow reuse after cancellation; service serializes reservation writes."""
from alembic import op
import sqlalchemy as sa

revision = '0004'
down_revision = '0003'
branch_labels = depends_on = None


def upgrade():
    with op.batch_alter_table('bookings') as batch:
        batch.drop_constraint('uq_booking_exact_dates', type_='unique')
    op.create_index('ix_booking_overlap', 'bookings', ['room_id', 'status', 'check_in', 'check_out'])


def downgrade():
    if op.get_bind().scalar(sa.text('SELECT COUNT(*) FROM (SELECT room_id, check_in, check_out FROM bookings GROUP BY room_id, check_in, check_out HAVING COUNT(*) > 1) AS duplicates')):
        raise RuntimeError('Cannot restore old uniqueness without removing history; downgrade refused')
    op.drop_index('ix_booking_overlap', table_name='bookings')
    with op.batch_alter_table('bookings') as batch:
        batch.create_unique_constraint('uq_booking_exact_dates', ['room_id', 'check_in', 'check_out'])
