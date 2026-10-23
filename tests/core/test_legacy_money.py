import os,subprocess,sys
from datetime import date
from decimal import Decimal
from sqlalchemy import text,select
from core.db_engine import build_engine
from backend.models import RoomType,Room,Customer,Booking,Invoice,Payment


def test_migration_marks_unrecorded_paid_balance_without_double_counting(tmp_path):
    url='sqlite:///'+(tmp_path/'legacy-money.db').as_posix()
    env=dict(os.environ,DATABASE_URL=url)
    assert subprocess.run([sys.executable,'-m','alembic','upgrade','0012'],env=env,capture_output=True).returncode==0
    engine=build_engine(url)
    try:
        with engine.begin() as db:
            db.execute(RoomType.__table__.insert(),{'id':1,'name':'Demo','capacity':2,'nightly_rate':900000})
            db.execute(Room.__table__.insert(),{'id':1,'number':'302','floor':3,'room_type_id':1})
            db.execute(Customer.__table__.insert(),{'id':1,'full_name':'Demo','phone':'0000000000'})
            db.execute(Booking.__table__.insert(),{'id':1,'code':'LEGACY','customer_id':1,'room_id':1,'check_in':date(2030,1,10),'check_out':date(2030,1,12),'guests':2,'booked_nightly_rate':900000})
            db.execute(Invoice.__table__.insert(),{'id':1,'booking_id':1,'room_amount':1800000,'total':1800000,'paid_amount':700000})
            db.execute(Payment.__table__.insert(),{'invoice_id':1,'amount':200000})
        assert subprocess.run([sys.executable,'-m','alembic','upgrade','head'],env=env,capture_output=True).returncode==0
        with engine.connect() as db:
            rows=db.execute(text('SELECT kind,amount FROM money_entries ORDER BY id')).all()
            assert [r[0] for r in rows]==['payment','legacy_opening']
            assert sum(Decimal(str(r[1])) for r in rows)==700000
            assert db.scalar(text('SELECT COUNT(*) FROM payments'))==1
    finally:engine.dispose()
