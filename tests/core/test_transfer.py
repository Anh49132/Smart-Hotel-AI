from decimal import Decimal
import os
from uuid import uuid4
import pytest
from sqlalchemy import select, text
from core.database import Base
from core.db_engine import build_engine
from backend.models import RoomType, User
from scripts.transfer_sqlite import transfer


@pytest.fixture(params=['sqlite', 'postgresql'])
def target_url(tmp_path, request):
    if request.param == 'sqlite':
        yield 'sqlite:///' + (tmp_path / 'target.db').as_posix()
        return
    if not os.environ.get('HOTEL_TEST_DATABASE_URL'):
        pytest.skip('Set HOTEL_TEST_DATABASE_URL for PostgreSQL transfer tests')
    admin = build_engine(os.environ['HOTEL_TEST_DATABASE_URL'])
    schema = 'hotel_transfer_' + uuid4().hex
    try:
        with admin.begin() as db:
            db.execute(text(f'CREATE SCHEMA "{schema}"'))
        yield admin.url.update_query_dict({'options': f'-csearch_path={schema}'}).render_as_string(hide_password=False)
    finally:
        with admin.begin() as db:
            db.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        admin.dispose()


def test_transfer_preserves_ids_money_hashes_and_refuses_nonempty(tmp_path, target_url):
    source_path = tmp_path / 'source.db'
    source = build_engine('sqlite:///' + source_path.as_posix())
    target = build_engine(target_url)
    try:
        Base.metadata.create_all(source)
        Base.metadata.create_all(target)
        with source.begin() as db:
            db.execute(User.__table__.insert(), {'id': 7, 'username': 'test', 'full_name': 'Test', 'password_hash': 'kept-hash', 'role': 'admin', 'is_active': True})
            db.execute(RoomType.__table__.insert(), {'id': 9, 'name': 'Suite', 'capacity': 2, 'nightly_rate': Decimal('850000.25'), 'amenities': ''})
        counts = transfer(source_path, target_url)
        assert counts['users'] == 1
        with target.connect() as db:
            assert db.scalar(select(User.password_hash)) == 'kept-hash'
            assert db.scalar(select(RoomType.nightly_rate)) == Decimal('850000.25')
        with pytest.raises(ValueError, match='empty'):
            transfer(source_path, target_url)
        with source.connect() as db:
            assert db.scalar(select(User.id)) == 7
        if target.dialect.name == 'postgresql':
            with target.begin() as db:
                inserted = db.execute(User.__table__.insert().returning(User.id), {'username': 'next', 'full_name': 'Next', 'password_hash': 'next-hash', 'role': 'admin', 'is_active': True}).scalar_one()
                assert inserted == 8
    finally:
        source.dispose()
        target.dispose()
