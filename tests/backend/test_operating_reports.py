from datetime import date,datetime
from decimal import Decimal
from sqlalchemy import select
from backend.models import Room,RoomStay,RoomBlock,BookingStatus,MoneyEntry,Invoice,FinancialAdjustment
from backend.schemas.inputs import ReceiptIn
from backend.services.booking_service import create_booking
from backend.services.money_service import receipt
from backend.services.invoice_service import invoice
from backend.services.reports_service import operating_report,report_csv
from tests.backend.test_booking_consistency import data


def test_month_boundary_moves_and_maintenance_union(db):
    db.add_all([Room(id=2,number='303',floor=3,room_type_id=1),Room(id=3,number='304',floor=3,room_type_id=1)]);db.commit()
    b=create_booking(db,data().model_copy(update={'check_in':date(2030,1,31),'check_out':date(2030,2,2)}))
    first=db.scalar(select(RoomStay).where(RoomStay.booking_id==b.id));first.check_out=date(2030,2,1)
    db.add(RoomStay(booking_id=b.id,room_id=2,check_in=date(2030,2,1),check_out=date(2030,2,2)))
    for _ in range(2):db.add(RoomBlock(room_id=3,start_date=date(2030,1,31),end_date=date(2030,2,2),description='Khóa bảo trì thử nghiệm',created_by=1))
    db.commit()
    jan=operating_report(db,date(2030,1,31),date(2030,2,1))
    feb=operating_report(db,date(2030,2,1),date(2030,2,2))
    assert jan['allocated_nights']==feb['allocated_nights']==1
    assert jan['blocked_nights']==feb['blocked_nights']==1
    assert jan['occupancy']==feb['occupancy']==50
    b.status=BookingStatus.no_show;db.commit()
    assert operating_report(db,date(2030,1,31),date(2030,2,2))['allocated_nights']==0


def test_cash_dates_adjustments_opening_and_csv_privacy(client,db):
    b=create_booking(db,data())
    inv=invoice(b.id,None,db);inv.issued_at=datetime(2030,1,9,16,59)
    receipt(db,b.id,ReceiptIn(amount=500000,kind='payment',request_key='report-cash-key'),1)
    entry=db.scalar(select(MoneyEntry));entry.occurred_at=datetime(2030,1,9,17)
    db.add(MoneyEntry(booking_id=b.id,amount=100000,kind='legacy_opening',method='unknown',request_key='legacy-opening-report',reference='private-ref',occurred_at=datetime(2030,1,10)))
    db.add(MoneyEntry(booking_id=b.id,amount=100000,kind='refund',method='cash',request_key='report-refund',reason='Private guest reason',occurred_at=datetime(2030,1,10)))
    db.add(FinancialAdjustment(booking_id=b.id,target_status='cancelled',original_total=1800000,fee_amount=180000,percent=10,amount=-1620000,reason='private note',request_key='report-cancel',actor_id=1,created_at=datetime(2030,1,10)))
    db.commit()
    report=operating_report(db,date(2030,1,10),date(2030,1,11))
    assert report['invoice_gross']==0 and report['invoice_net']==-1620000
    assert report['received']==500000 and report['refunded']==100000 and report['net_cash']==400000
    assert report['legacy_opening_excluded']==100000
    assert report['credits_now']==320000
    export=report_csv(report)
    assert all(secret not in export for secret in ('Nguyễn An','0900000000','private','Private',b.code))
    assert client.get('/reports?start=2030-01-10&end=2030-01-11').status_code==200
    assert client.get('/api/reports/operations.csv?start=2030-01-10&end=2030-01-11').headers['cache-control']=='no-store'
    assert client.get('/api/reports/operations?start=2030-01-10&end=2030-01-10').status_code==422
