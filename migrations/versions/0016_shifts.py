"""Explicit cashier shifts; old transactions retain a null shift, never fabricated."""
from alembic import op
import sqlalchemy as sa
revision='0016'
down_revision='0015'
branch_labels=depends_on=None

def upgrade():
    op.create_table('cashier_shifts',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('cashier_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('status',sa.String(10),nullable=False),sa.Column('opened_at',sa.DateTime(),nullable=False),sa.Column('closed_at',sa.DateTime()),sa.Column('opening_cash',sa.Numeric(12,2),nullable=False),sa.Column('counted_cash',sa.Numeric(12,2)),sa.Column('expected_cash',sa.Numeric(14,2)),sa.Column('difference',sa.Numeric(14,2)),sa.Column('handed_to',sa.Integer(),sa.ForeignKey('users.id')),sa.Column('note',sa.String(2000),nullable=False),sa.Column('snapshot_json',sa.Text(),nullable=False),sa.CheckConstraint("status IN ('open','closed')",name='ck_shift_status'),sa.CheckConstraint('opening_cash >= 0 AND (counted_cash IS NULL OR counted_cash >= 0)',name='ck_shift_amounts'))
    op.create_index('uq_shift_open_cashier','cashier_shifts',['cashier_id'],unique=True,sqlite_where=sa.text("status='open'"),postgresql_where=sa.text("status='open'"))
    with op.batch_alter_table('money_entries') as b:
        b.add_column(sa.Column('shift_id',sa.Integer(),nullable=True))
        b.create_foreign_key('fk_money_shift','cashier_shifts',['shift_id'],['id'])
        b.create_index('ix_money_entries_shift_id',['shift_id'])

def downgrade():
    if op.get_bind().execute(sa.text('SELECT COUNT(*) FROM cashier_shifts')).scalar():raise RuntimeError('Preserve shift records before downgrade')
    with op.batch_alter_table('money_entries') as b:
        b.drop_index('ix_money_entries_shift_id');b.drop_constraint('fk_money_shift',type_='foreignkey');b.drop_column('shift_id')
    op.drop_index('uq_shift_open_cashier',table_name='cashier_shifts');op.drop_table('cashier_shifts')
