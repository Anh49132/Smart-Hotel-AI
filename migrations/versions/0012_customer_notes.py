"""Private guest preferences; legacy rows start empty."""
from alembic import op
import sqlalchemy as sa
revision='0012'
down_revision='0011'
branch_labels=depends_on=None


def upgrade():
    with op.batch_alter_table('customers') as b:
        b.add_column(sa.Column('preference_notes',sa.Text(),nullable=False,server_default=''))


def downgrade():
    with op.batch_alter_table('customers') as b:b.drop_column('preference_notes')
