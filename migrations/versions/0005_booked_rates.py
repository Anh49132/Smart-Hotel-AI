"""Snapshot booking rates and validate invoice arithmetic before constraints."""
from decimal import Decimal, ROUND_HALF_UP
from alembic import op
import sqlalchemy as sa

revision = '0005'
down_revision = '0004'
branch_labels = depends_on = None

CHECKS = [
    ('ck_invoice_amounts','room_amount >= 0 AND service_amount >= 0'),
    ('ck_invoice_discount','discount >= 0 AND discount <= room_amount + service_amount'),
    ('ck_invoice_total','total = room_amount + service_amount - discount'),
    ('ck_invoice_paid','paid_amount >= 0 AND paid_amount <= total'),
]


def upgrade():
    bind=op.get_bind()
    for name,expression in CHECKS:
        if bind.scalar(sa.text(f'SELECT COUNT(*) FROM invoices WHERE NOT ({expression})')):
            raise RuntimeError(f'Legacy invoice data violates {name}; reconcile a backup before upgrading')
    op.add_column('bookings',sa.Column('booked_nightly_rate',sa.Numeric(12,2),nullable=True))
    op.add_column('bookings',sa.Column('booked_rate_source',sa.String(24),nullable=True,server_default='confirmed'))
    metadata=sa.MetaData()
    bookings=sa.Table('bookings',metadata,autoload_with=bind)
    rooms=sa.Table('rooms',metadata,autoload_with=bind)
    types=sa.Table('room_types',metadata,autoload_with=bind)
    invoices=sa.Table('invoices',metadata,autoload_with=bind)
    query=sa.select(bookings.c.id,bookings.c.check_in,bookings.c.check_out,types.c.nightly_rate,invoices.c.room_amount).select_from(bookings.join(rooms,rooms.c.id==bookings.c.room_id).join(types,types.c.id==rooms.c.room_type_id).outerjoin(invoices,invoices.c.booking_id==bookings.c.id))
    for row in bind.execute(query).mappings().all():
        nights=(row['check_out']-row['check_in']).days
        rate=Decimal(row['room_amount'])/nights if row['room_amount'] is not None else Decimal(row['nightly_rate'])
        rate=rate.quantize(Decimal('.01'),rounding=ROUND_HALF_UP)
        source='legacy_invoice' if row['room_amount'] is not None else 'legacy_current_rate'
        bind.execute(bookings.update().where(bookings.c.id==row['id']).values(booked_nightly_rate=rate,booked_rate_source=source))
    with op.batch_alter_table('bookings') as batch:
        batch.alter_column('booked_nightly_rate',existing_type=sa.Numeric(12,2),nullable=False)
        batch.alter_column('booked_rate_source',existing_type=sa.String(24),nullable=False)
        batch.create_check_constraint('ck_booking_rate','booked_nightly_rate >= 0')
    with op.batch_alter_table('invoices') as batch:
        for name,expression in CHECKS:
            batch.create_check_constraint(name,expression)


def downgrade():
    with op.batch_alter_table('invoices') as batch:
        for name,_ in CHECKS:
            batch.drop_constraint(name,type_='check')
    with op.batch_alter_table('bookings') as batch:
        batch.drop_constraint('ck_booking_rate',type_='check')
        batch.drop_column('booked_rate_source')
        batch.drop_column('booked_nightly_rate')
