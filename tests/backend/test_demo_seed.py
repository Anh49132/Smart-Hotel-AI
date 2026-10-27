from datetime import date
from decimal import Decimal
from sqlalchemy import select,func,delete
import pytest
from fastapi import HTTPException
from core.database import Base
from backend.models import User,Invoice,Booking,MoneyEntry,Room,DemoSeed
from backend.services.demo_service import extend_existing_demo_months,seed_demo
import backend.services.demo_service as demo_service
from backend.services.folio_service import folio
from backend.services.money_service import net_received
from backend.services.reports_service import operating_report

def test_demo_refuses_operational_data(db):
    with pytest.raises(HTTPException) as error:seed_demo(db,'PrivateDemo@2030')
    assert error.value.status_code==409
    assert db.scalar(select(func.count()).select_from(User))==1

def test_seed_is_consistent_repeatable_and_never_resets_staff(db):
    # Only the fixture's isolated schema is cleared, retaining its admin.
    for table in reversed(Base.metadata.sorted_tables):
        if table.name!='users':db.execute(delete(table))
    db.commit()
    result=seed_demo(db,'PrivateDemo@2030');assert not result['already_seeded']
    assert db.scalar(select(func.count()).select_from(Room))==12
    assert db.scalar(select(func.count()).select_from(Booking))==33
    assert db.get(DemoSeed,'lotus-demo-v1')
    monthly=db.scalars(select(Booking).where(Booking.code.like(f"DEMO-{db.get(DemoSeed,'lotus-demo-v1').anchor_date.year}-%"))).all()
    assert len(monthly)==12
    assert {booking.check_in.month for booking in monthly}=={8,9,10,11}
    assert db.get(DemoSeed,'lotus-demo-months-v1')
    year=db.get(DemoSeed,'lotus-demo-v1').anchor_date.year
    for month in (8,9,10,11):
        report=operating_report(db,date(year,month,1),date(year,month+1,1))
        assert report['booking_count']>=3 and report['allocated_nights']>0
    people={u.username:u.password_hash for u in db.scalars(select(User))}
    counts={t.name:db.scalar(select(func.count()).select_from(t)) for t in Base.metadata.sorted_tables}
    assert seed_demo(db,'ChangedPrivate@2030')['already_seeded']
    assert counts=={t.name:db.scalar(select(func.count()).select_from(t)) for t in Base.metadata.sorted_tables}
    assert people=={u.username:u.password_hash for u in db.scalars(select(User))}
    for inv in db.scalars(select(Invoice)):
        f=folio(db,inv.booking_id)
        assert sum(Decimal(line['amount']) for line in f['lines'])==Decimal(f['total'])
        assert inv.paid_amount==net_received(db,inv.booking_id)

def test_existing_v1_demo_gets_monthly_samples_without_reseeding(db,monkeypatch):
    for table in reversed(Base.metadata.sorted_tables):
        if table.name!='users':db.execute(delete(table))
    db.commit()
    original=demo_service.seed_monthly_samples
    monkeypatch.setattr(demo_service,'seed_monthly_samples',lambda *args:0)
    first=seed_demo(db,'PrivateDemo@2030',anchor=date(2026,10,27))
    assert not first['already_seeded']
    assert db.scalar(select(func.count()).select_from(Booking))==21

    monkeypatch.setattr(demo_service,'seed_monthly_samples',original)
    upgraded=extend_existing_demo_months(db,anchor=date(2026,10,27))
    assert upgraded=={'already_seeded':True,'monthly_bookings_added':12}
    assert db.scalar(select(func.count()).select_from(Booking))==33
    assert extend_existing_demo_months(db,anchor=date(2026,10,27))=={'already_seeded':True,'monthly_bookings_added':0}
