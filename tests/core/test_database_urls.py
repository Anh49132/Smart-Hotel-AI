import pytest
from core.db_engine import normalize_database_url


@pytest.mark.parametrize('scheme', ['postgres', 'postgresql', 'postgresql+psycopg'])
def test_postgres_urls_keep_credentials_and_tls(scheme):
    url = normalize_database_url(f'{scheme}://user:pass@localhost:5432/hotel?sslmode=require')
    assert url.drivername == 'postgresql+psycopg'
    assert url.password == 'pass'
    assert url.query['sslmode'] == 'require'


def test_sqlite_relative_url_is_absolute():
    from pathlib import Path
    assert Path(normalize_database_url('sqlite:///./data/hotel.db').database).is_absolute()
