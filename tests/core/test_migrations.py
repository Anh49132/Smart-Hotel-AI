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


def test_sqlite_batch_upgrade_preserves_referenced_history(tmp_path):
    from datetime import date
    from backend.models import Booking, BookingStatusHistory, Customer, Invoice, Room, RoomType
    url = 'sqlite:///' + (tmp_path / 'existing.db').as_posix()
    env = dict(os.environ, DATABASE_URL=url)
    result = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', '0002'], env=env, capture_output=True)
    assert result.returncode == 0
    engine = build_engine(url)
    try:
        with engine.begin() as db:
            db.execute(RoomType.__table__.insert(), {'id':1,'name':'Deluxe','capacity':2,'nightly_rate':900000,'amenities':''})
            db.execute(Room.__table__.insert(), {'id':1,'number':'302','floor':3,'room_type_id':1})
            db.execute(Customer.__table__.insert(), {'id':1,'full_name':'Demo','phone':'0000000000'})
            db.execute(Booking.__table__.insert(), {'id':1,'code':'BK-LEGACY','customer_id':1,'room_id':1,'check_in':date(2030,1,1),'check_out':date(2030,1,3),'guests':2})
            db.execute(Invoice.__table__.insert(), {'id':1,'booking_id':1,'room_amount':1800000,'total':1800000})
            db.execute(BookingStatusHistory.__table__.insert(), {'booking_id':1,'to_status':'confirmed'})
        result = subprocess.run([sys.executable, '-m', 'alembic', 'upgrade', 'head'], env=env, capture_output=True, text=True)
        assert result.returncode == 0, result.stderr
        with engine.connect() as db:
            assert db.scalar(text('SELECT total FROM invoices WHERE id=1')) == 1800000
            assert db.scalar(text('SELECT COUNT(*) FROM booking_status_history')) == 1
            assert db.exec_driver_sql('PRAGMA foreign_key_check').fetchall() == []
    finally:
        engine.dispose()
