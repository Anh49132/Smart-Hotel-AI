from backend.models import Customer,Role
from backend.services.booking_service import create_booking
from tests.backend.test_booking_consistency import data
from tests.backend.test_staff_security import staff,token

def test_pdf_documents_escape_text_embed_fonts_and_enforce_permissions(client,db):
    db.get(Customer,1).full_name='Nguyễn An <test & review>';db.commit()
    b=create_booking(db,data())
    receipt=client.post(f'/api/bookings/{b.id}/receipts',json={'amount':100000,'request_key':'pdf-deposit-test'}).json()
    for path in [f'/bookings/{b.id}/folio.pdf',f"/receipts/{receipt['id']}/document.pdf"]:
        response=client.get(path)
        assert response.status_code==200 and response.content.startswith(b'%PDF-')
        assert len(response.content)>10000 and response.headers['cache-control']=='no-store'
    clerk=staff(db,Role.receptionist);client.cookies.set('access_token',token(clerk))
    assert client.get(f'/bookings/{b.id}/folio.pdf').status_code==403
    assert client.get(f"/receipts/{receipt['id']}/document.pdf").status_code==403
