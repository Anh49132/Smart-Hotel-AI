"""Append-only cancellation settlements and refund reasons."""
from alembic import op
import sqlalchemy as sa
revision='0015'
down_revision='0013'
branch_labels=depends_on=None


def upgrade():
    with op.batch_alter_table('money_entries') as b:b.add_column(sa.Column('reason',sa.String(500),nullable=False,server_default=''))
    with op.batch_alter_table('hotel_policy') as b:
        b.add_column(sa.Column('cancellation_percent',sa.Numeric(5,2),nullable=False,server_default='0'))
        b.add_column(sa.Column('no_show_percent',sa.Numeric(5,2),nullable=False,server_default='0'))
        b.create_check_constraint('ck_policy_cancellation','cancellation_percent BETWEEN 0 AND 100 AND no_show_percent BETWEEN 0 AND 100')
    op.create_table('financial_adjustments',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('booking_id',sa.Integer(),sa.ForeignKey('bookings.id'),nullable=False,unique=True),sa.Column('target_status',sa.String(20),nullable=False),sa.Column('original_total',sa.Numeric(12,2),nullable=False),sa.Column('fee_amount',sa.Numeric(12,2),nullable=False),sa.Column('percent',sa.Numeric(5,2),nullable=False),sa.Column('amount',sa.Numeric(12,2),nullable=False),sa.Column('reason',sa.String(500),nullable=False),sa.Column('request_key',sa.String(64),nullable=False),sa.Column('actor_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False),sa.CheckConstraint("target_status IN ('cancelled','no_show')",name='ck_adjustment_status'),sa.CheckConstraint('percent >= 0 AND percent <= 100 AND fee_amount >= 0 AND fee_amount <= original_total AND amount = fee_amount - original_total',name='ck_adjustment_math'))


def downgrade():
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM money_entries WHERE kind='refund'")).scalar() or op.get_bind().execute(sa.text('SELECT COUNT(*) FROM financial_adjustments')).scalar():raise RuntimeError('Preserve refund and cancellation records before downgrade')
    op.drop_table('financial_adjustments')
    with op.batch_alter_table('hotel_policy') as b:b.drop_constraint('ck_policy_cancellation',type_='check');b.drop_column('no_show_percent');b.drop_column('cancellation_percent')
    with op.batch_alter_table('money_entries') as b:b.drop_column('reason')
