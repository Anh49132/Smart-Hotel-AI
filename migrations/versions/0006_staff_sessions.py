"""Revoke sessions after staff account changes."""
from alembic import op
import sqlalchemy as sa

revision = '0006'
down_revision = '0005'
branch_labels = depends_on = None


def upgrade():
    with op.batch_alter_table('users') as batch:
        batch.add_column(sa.Column('token_version', sa.Integer(), nullable=False, server_default='0'))
        batch.add_column(sa.Column('must_change_password', sa.Boolean(), nullable=False, server_default=sa.false()))


def downgrade():
    with op.batch_alter_table('users') as batch:
        batch.drop_column('must_change_password')
        batch.drop_column('token_version')
