"""Dated prices and immutable nightly booking snapshots."""
from alembic import op
import sqlalchemy as sa

revision = '0007'
down_revision = '0006'
branch_labels = depends_on = None


def upgrade():
    with op.batch_alter_table('room_types') as batch:
        batch.add_column(sa.Column('weekend_rate', sa.Numeric(12, 2), nullable=True))
        batch.add_column(sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()))
        batch.create_check_constraint('ck_room_type_weekend', 'weekend_rate IS NULL OR weekend_rate > 0')
    op.create_table('rate_plans',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('room_type_id', sa.Integer(), sa.ForeignKey('room_types.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('start_date', sa.Date(), nullable=False),
        sa.Column('end_date', sa.Date(), nullable=False),
        sa.Column('nightly_rate', sa.Numeric(12, 2), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.CheckConstraint('end_date > start_date', name='ck_rate_plan_dates'),
        sa.CheckConstraint('nightly_rate > 0', name='ck_rate_plan_price'))
    op.create_index('ix_rate_plans_room_type_id', 'rate_plans', ['room_type_id'])
    op.create_table('booking_nights',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('booking_id', sa.Integer(), sa.ForeignKey('bookings.id'), nullable=False),
        sa.Column('stay_date', sa.Date(), nullable=False),
        sa.Column('amount', sa.Numeric(12, 2), nullable=False),
        sa.Column('source', sa.String(120), nullable=False),
        sa.UniqueConstraint('booking_id', 'stay_date', name='uq_booking_night'),
        sa.CheckConstraint('amount >= 0', name='ck_booking_night_amount'))
    op.create_index('ix_booking_nights_booking_id', 'booking_nights', ['booking_id'])


def downgrade():
    op.drop_table('booking_nights')
    op.drop_table('rate_plans')
    with op.batch_alter_table('room_types') as batch:
        batch.drop_constraint('ck_room_type_weekend', type_='check')
        batch.drop_column('is_active')
        batch.drop_column('weekend_rate')
