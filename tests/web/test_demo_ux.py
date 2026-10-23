from datetime import date,timedelta
from backend.schemas.inputs import BookingIn
from backend.services.booking_service import create_booking
from backend.services.invoice_service import invoice

def test_booking_and_invoice_search_crosses_pages(client,db):
    for i in range(23):
        start=date(2030,1,10)+timedelta(days=i*3)
        b=create_booking(db,BookingIn(customer_id=1,room_id=1,check_in=start,check_out=start+timedelta(days=2),guests=2))
        b.code=f'PAGE-{i:02}';db.commit();invoice(b.id,None,db)
    for path,key in [('/bookings','bookings'),('/invoices','invoices')]:
        first=client.get(path);assert len(first.context[key])==20
        assert first.context['pagination']['total']==23
        second=client.get(path+'?page=2');assert len(second.context[key])==3
        found=client.get(path+'?q=PAGE-00');assert len(found.context[key])==1
        assert found.context['pagination']['total']==1
        assert client.get(path+'?q=%25').context['pagination']['total']==0
        assert client.get(path+'?status=invalid').status_code==422

def test_local_assets_are_available_without_third_party_cdn(client):
    for path in ['/static/vendor/bootstrap/bootstrap.min.css','/static/vendor/bootstrap/bootstrap.bundle.min.js','/static/vendor/bootstrap-icons/bootstrap-icons.min.css','/static/vendor/bootstrap-icons/fonts/bootstrap-icons.woff2','/static/js/operations-ux.js','/static/css/operations-ux.css']:
        assert client.get(path).status_code==200
    page=client.get('/bookings').text
    assert 'cdn.jsdelivr.net' not in page and 'fonts.googleapis.com' not in page
