"""Track idempotent synthetic demo data independently from operational records."""
from alembic import op
import sqlalchemy as sa
revision='0022'
down_revision='0019'
branch_labels=depends_on=None
def upgrade():
    op.create_table('demo_seeds',sa.Column('name',sa.String(60),primary_key=True),sa.Column('anchor_date',sa.Date(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False))
def downgrade():op.drop_table('demo_seeds')
