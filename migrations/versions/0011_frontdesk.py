"""No-show, hotel timing policy and explicitly confirmed surcharges."""
from alembic import op
import sqlalchemy as sa
revision='0011'
down_revision='0010'
branch_labels=depends_on=None


def upgrade():
    if op.get_bind().dialect.name=='postgresql': op.execute("ALTER TYPE bookingstatus ADD VALUE IF NOT EXISTS 'no_show'")
    with op.batch_alter_table('bookings') as b:
        b.add_column(sa.Column('actual_check_in',sa.DateTime()))
        b.add_column(sa.Column('actual_check_out',sa.DateTime()))
    with op.batch_alter_table('invoices') as b:
        b.add_column(sa.Column('surcharge_amount',sa.Numeric(12,2),nullable=False,server_default='0'))
        b.drop_constraint('ck_invoice_discount',type_='check');b.drop_constraint('ck_invoice_total',type_='check')
        b.create_check_constraint('ck_invoice_discount','discount >= 0 AND discount <= room_amount + service_amount + surcharge_amount')
        b.create_check_constraint('ck_invoice_total','total = room_amount + service_amount + surcharge_amount - discount')
        b.create_check_constraint('ck_invoice_surcharge','surcharge_amount >= 0')
    op.create_table('hotel_policy',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('check_in_hour',sa.Integer(),nullable=False),sa.Column('check_out_hour',sa.Integer(),nullable=False),sa.Column('no_show_hour',sa.Integer(),nullable=False),sa.Column('early_fee',sa.Numeric(12,2),nullable=False),sa.Column('late_fee',sa.Numeric(12,2),nullable=False),sa.CheckConstraint('id=1',name='ck_policy_singleton'),sa.CheckConstraint('check_in_hour BETWEEN 0 AND 23 AND check_out_hour BETWEEN 0 AND 23 AND no_show_hour BETWEEN 0 AND 23',name='ck_policy_hours'),sa.CheckConstraint('early_fee >= 0 AND late_fee >= 0',name='ck_policy_fees'))
    op.create_table('booking_surcharges',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('booking_id',sa.Integer(),sa.ForeignKey('bookings.id'),nullable=False),sa.Column('kind',sa.String(10),nullable=False),sa.Column('amount',sa.Numeric(12,2),nullable=False),sa.Column('confirmed_by',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('confirmed_at',sa.DateTime(),nullable=False),sa.UniqueConstraint('booking_id','kind',name='uq_booking_surcharge'),sa.CheckConstraint("kind IN ('early','late')",name='ck_surcharge_kind'),sa.CheckConstraint('amount > 0',name='ck_surcharge_amount'))
    op.create_index('ix_booking_surcharges_booking_id','booking_surcharges',['booking_id'])


def downgrade():
    bind=op.get_bind()
    if bind.execute(sa.text("SELECT COUNT(*) FROM bookings WHERE status='no_show'")).scalar() or bind.execute(sa.text('SELECT COUNT(*) FROM booking_surcharges')).scalar():
        raise RuntimeError('Preserve no-show and surcharge history before downgrading')
    op.drop_table('booking_surcharges');op.drop_table('hotel_policy')
    with op.batch_alter_table('invoices') as b:
        b.drop_constraint('ck_invoice_discount',type_='check');b.drop_constraint('ck_invoice_total',type_='check');b.drop_constraint('ck_invoice_surcharge',type_='check')
        b.drop_column('surcharge_amount')
        b.create_check_constraint('ck_invoice_discount','discount >= 0 AND discount <= room_amount + service_amount')
        b.create_check_constraint('ck_invoice_total','total = room_amount + service_amount - discount')
    with op.batch_alter_table('bookings') as b:
        b.drop_column('actual_check_out');b.drop_column('actual_check_in')
    if bind.dialect.name=='postgresql':
        op.execute('ALTER TYPE bookingstatus RENAME TO bookingstatus_with_no_show')
        op.execute("CREATE TYPE bookingstatus AS ENUM ('confirmed','checked_in','checked_out','cancelled')")
        for table,col in [('bookings','status'),('booking_status_history','from_status'),('booking_status_history','to_status')]:
            op.execute(f'ALTER TABLE {table} ALTER COLUMN {col} TYPE bookingstatus USING {col}::text::bookingstatus')
        op.execute('DROP TYPE bookingstatus_with_no_show')
