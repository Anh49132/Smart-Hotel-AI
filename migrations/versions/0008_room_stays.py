"""Room assignment segments and reservation change audit."""
from alembic import op
import sqlalchemy as sa

revision = '0008'
down_revision = '0007'
branch_labels = depends_on = None


def upgrade():
    op.create_table('room_stays', sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('booking_id', sa.Integer(), sa.ForeignKey('bookings.id'), nullable=False),
        sa.Column('room_id', sa.Integer(), sa.ForeignKey('rooms.id'), nullable=False),
        sa.Column('check_in', sa.Date(), nullable=False), sa.Column('check_out', sa.Date(), nullable=False),
        sa.CheckConstraint('check_out > check_in', name='ck_stay_dates'))
    op.create_index('ix_room_stays_booking_id','room_stays',['booking_id'])
    op.create_index('ix_stay_overlap','room_stays',['room_id','check_in','check_out'])
    op.execute('INSERT INTO room_stays (booking_id, room_id, check_in, check_out) SELECT id, room_id, check_in, check_out FROM bookings')
    op.create_table('booking_changes', sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('booking_id', sa.Integer(), sa.ForeignKey('bookings.id'), nullable=False),
        sa.Column('changed_by', sa.Integer(), sa.ForeignKey('users.id')),
        sa.Column('reason',sa.String(500),nullable=False), sa.Column('before_data',sa.Text(),nullable=False),
        sa.Column('after_data',sa.Text(),nullable=False), sa.Column('changed_at',sa.DateTime(),nullable=False))
    op.create_index('ix_booking_changes_booking_id','booking_changes',['booking_id'])


def downgrade():
    op.drop_table('booking_changes')
    op.drop_table('room_stays')
