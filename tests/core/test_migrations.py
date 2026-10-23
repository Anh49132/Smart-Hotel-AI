import os
import subprocess
import sys
from uuid import uuid4

import pytest
from sqlalchemy import text
from core.db_engine import build_engine


@pytest.mark.parametrize('backend', ['sqlite', 'postgresql'])
def test_upgrade_check_downgrade_upgrade(tmp_path, backend):
    schema = None
    admin = None
    if backend == 'postgresql':
        if not os.environ.get('HOTEL_TEST_DATABASE_URL'):
            pytest.skip('Set HOTEL_TEST_DATABASE_URL to test PostgreSQL in an isolated schema')
        admin = build_engine(os.environ['HOTEL_TEST_DATABASE_URL'])
        schema = 'hotel_migration_' + uuid4().hex
        with admin.begin() as db:
            db.execute(text(f'CREATE SCHEMA "{schema}"'))
        url = admin.url.update_query_dict({'options': f'-csearch_path={schema}'}).render_as_string(hide_password=False)
    else:
        url = 'sqlite:///' + (tmp_path / 'migration.db').as_posix()
    try:
        env = dict(os.environ, DATABASE_URL=url)
        for args in [('upgrade', 'head'), ('check',), ('downgrade', 'base'), ('upgrade', 'head'), ('check',)]:
            result = subprocess.run([sys.executable, '-m', 'alembic', *args], env=env, capture_output=True, text=True)
            # Keep credentials out of a failed assertion's diagnostic text.
            assert result.returncode == 0, f'alembic {args}: {result.stderr.replace(url, "[DATABASE_URL]")}'
    finally:
        if admin is not None:
            with admin.begin() as db:
                db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            admin.dispose()
