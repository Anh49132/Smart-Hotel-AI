"""Dated maintenance inventory blocks."""
from alembic import op
import sqlalchemy as sa
revision='0010'
down_revision='0009'
branch_labels=depends_on=None


def upgrade():
    op.create_table('room_blocks',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('room_id',sa.Integer(),sa.ForeignKey('rooms.id'),nullable=False),
        sa.Column('start_date',sa.Date(),nullable=False),sa.Column('end_date',sa.Date(),nullable=False),
        sa.Column('description',sa.String(500),nullable=False),sa.Column('status',sa.String(20),nullable=False),
        sa.Column('assigned_to',sa.Integer(),sa.ForeignKey('users.id')),
        sa.Column('created_by',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),
        sa.Column('created_at',sa.DateTime(),nullable=False),sa.Column('resolved_at',sa.DateTime()),
        sa.CheckConstraint('end_date > start_date',name='ck_block_dates'),
        sa.CheckConstraint("status IN ('open','in_progress','resolved','cancelled')",name='ck_block_status'))
    op.create_index('ix_block_overlap','room_blocks',['room_id','start_date','end_date'])


def downgrade():
    op.drop_table('room_blocks')
