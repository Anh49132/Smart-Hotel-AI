from decimal import Decimal
from sqlalchemy import select,func,delete
import pytest
from fastapi import HTTPException
from core.database import Base
from backend.models import User,Invoice,Booking,MoneyEntry,Room,DemoSeed
from backend.services.demo_service import seed_demo
from backend.services.folio_service import folio
from backend.services.money_service import net_received

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
    assert db.scalar(select(func.count()).select_from(Booking))==21
    assert db.get(DemoSeed,'lotus-demo-v1')
    people={u.username:u.password_hash for u in db.scalars(select(User))}
    counts={t.name:db.scalar(select(func.count()).select_from(t)) for t in Base.metadata.sorted_tables}
    assert seed_demo(db,'ChangedPrivate@2030')['already_seeded']
    assert counts=={t.name:db.scalar(select(func.count()).select_from(t)) for t in Base.metadata.sorted_tables}
    assert people=={u.username:u.password_hash for u in db.scalars(select(User))}
    for inv in db.scalars(select(Invoice)):
        f=folio(db,inv.booking_id)
        assert sum(Decimal(line['amount']) for line in f['lines'])==Decimal(f['total'])
        assert inv.paid_amount==net_received(db,inv.booking_id)
