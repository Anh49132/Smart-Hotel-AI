"""Housekeeping accounts and verifiable room readiness."""
from alembic import op
import sqlalchemy as sa

revision='0009'
down_revision='0008'
branch_labels=depends_on=None


def upgrade():
    if op.get_bind().dialect.name=='postgresql':
        op.execute("ALTER TYPE role ADD VALUE IF NOT EXISTS 'housekeeping'")
    op.create_table('cleaning_tasks',sa.Column('id',sa.Integer(),primary_key=True),
        sa.Column('room_id',sa.Integer(),sa.ForeignKey('rooms.id'),nullable=False),
        sa.Column('assigned_to',sa.Integer(),sa.ForeignKey('users.id')),
        sa.Column('status',sa.String(20),nullable=False), sa.Column('created_at',sa.DateTime(),nullable=False),
        sa.Column('started_at',sa.DateTime()),sa.Column('completed_at',sa.DateTime()),
        sa.Column('inspected_at',sa.DateTime()),sa.Column('inspected_by',sa.Integer(),sa.ForeignKey('users.id')),
        sa.CheckConstraint("status IN ('pending','in_progress','inspection','ready')",name='ck_cleaning_status'))
    op.create_index('ix_cleaning_tasks_room_id','cleaning_tasks',['room_id'])
    # Keep old cleaning rooms in the inspection workflow without inventing completion times.
    op.execute("INSERT INTO cleaning_tasks (room_id,status,created_at) SELECT id,'pending',CURRENT_TIMESTAMP FROM rooms WHERE status='cleaning'")


def downgrade():
    if op.get_bind().execute(sa.text("SELECT COUNT(*) FROM users WHERE role='housekeeping'")).scalar():
        raise RuntimeError('Reassign housekeeping accounts before downgrading the role schema')
    op.drop_table('cleaning_tasks')
    if op.get_bind().dialect.name=='postgresql':
        op.execute('ALTER TYPE role RENAME TO role_with_housekeeping')
        op.execute("CREATE TYPE role AS ENUM ('admin','receptionist','accountant')")
        op.execute('ALTER TABLE users ALTER COLUMN role TYPE role USING role::text::role')
        op.execute('DROP TYPE role_with_housekeeping')
