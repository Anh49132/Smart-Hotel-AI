"""Canonical receipt ledger with explicit legacy reconciliation, no double counting."""
from alembic import op
import sqlalchemy as sa
from decimal import Decimal
from datetime import datetime

revision='0013'
down_revision='0012'
branch_labels=depends_on=None


def upgrade():
    entries=op.create_table('money_entries',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('booking_id',sa.Integer(),sa.ForeignKey('bookings.id'),nullable=False),
        sa.Column('payment_id',sa.Integer(),sa.ForeignKey('payments.id'),unique=True),
        sa.Column('amount',sa.Numeric(12,2),nullable=False),sa.Column('kind',sa.String(20),nullable=False),
        sa.Column('method',sa.String(20),nullable=False),sa.Column('reference',sa.String(100),nullable=False),
        sa.Column('request_key',sa.String(64),nullable=False),sa.Column('actor_id',sa.Integer(),sa.ForeignKey('users.id')),
        sa.Column('occurred_at',sa.DateTime(),nullable=False),
        sa.UniqueConstraint('booking_id','request_key',name='uq_money_request'),sa.CheckConstraint('amount > 0',name='ck_money_positive'),
        sa.CheckConstraint("kind IN ('deposit','payment','refund','legacy_opening')",name='ck_money_kind'),
        sa.CheckConstraint("method IN ('cash','bank_transfer','unknown')",name='ck_money_method'))
    op.create_index('ix_money_entries_booking_id','money_entries',['booking_id'])
    bind=op.get_bind()
    def stamp(value):return value if isinstance(value,datetime) else datetime.fromisoformat(value)
    for inv in bind.execute(sa.text('SELECT id,booking_id,paid_amount,issued_at FROM invoices')).mappings().all():
        paid=Decimal(str(inv['paid_amount']))
        payments=bind.execute(sa.text('SELECT id,amount,paid_by,paid_at FROM payments WHERE invoice_id=:id'),{'id':inv['id']}).mappings().all()
        recorded=sum((Decimal(str(p['amount'])) for p in payments),Decimal(0))
        if recorded>paid:raise RuntimeError('Payment history exceeds paid balance; reconcile source data before migration')
        for p in payments:
            bind.execute(entries.insert(),{'booking_id':inv['booking_id'],'payment_id':p['id'],'amount':Decimal(str(p['amount'])),'kind':'payment','method':'unknown','reference':'','request_key':f"legacy-payment-{p['id']}",'actor_id':p['paid_by'],'occurred_at':stamp(p['paid_at'])})
        if paid>recorded:
            bind.execute(entries.insert(),{'booking_id':inv['booking_id'],'amount':paid-recorded,'kind':'legacy_opening','method':'unknown','reference':'Opening balance; actual receipt time unknown','request_key':f"legacy-opening-{inv['id']}",'occurred_at':stamp(inv['issued_at'])})


def downgrade():
    bind=op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM money_entries WHERE request_key NOT LIKE 'legacy-%'")).scalar():
        raise RuntimeError('New financial records cannot be represented in the old payment schema')
    op.drop_table('money_entries')
