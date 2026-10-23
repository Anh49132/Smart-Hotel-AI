"""Record AI provenance without attributing legacy drafts to a fabricated model."""
from alembic import op
import sqlalchemy as sa
revision='0019'
down_revision='0016'
branch_labels=depends_on=None

def upgrade():
    with op.batch_alter_table('ai_results') as b:
        b.add_column(sa.Column('email_kind',sa.String(30),nullable=False,server_default=''))
        b.add_column(sa.Column('model_name',sa.String(80),nullable=False,server_default='legacy/unknown'))
        b.add_column(sa.Column('prompt_version',sa.String(40),nullable=False,server_default='legacy/unknown'))
        b.add_column(sa.Column('source_json',sa.Text(),nullable=False,server_default='{}'))
    op.create_table('ai_review_events',sa.Column('id',sa.Integer(),primary_key=True),sa.Column('result_id',sa.Integer(),sa.ForeignKey('ai_results.id'),nullable=False),sa.Column('actor_id',sa.Integer(),sa.ForeignKey('users.id'),nullable=False),sa.Column('approved',sa.Boolean(),nullable=False),sa.Column('created_at',sa.DateTime(),nullable=False))
    op.create_index('ix_ai_review_events_result_id','ai_review_events',['result_id'])

def downgrade():
    if op.get_bind().execute(sa.text('SELECT COUNT(*) FROM ai_review_events')).scalar():raise RuntimeError('Preserve AI review history before downgrade')
    op.drop_table('ai_review_events')
    with op.batch_alter_table('ai_results') as b:
        for name in ('source_json','prompt_version','model_name','email_kind'):b.drop_column(name)
