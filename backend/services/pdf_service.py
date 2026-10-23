"""Generate internal documents with embedded Vietnamese fonts and escaped data."""
from io import BytesIO
from decimal import Decimal
from threading import Lock
from xml.sax.saxutils import escape
from core.config import FRONTEND_DIR
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,KeepTogether

_font_lock=Lock()
def styles():
    with _font_lock:
        if 'HotelNoto' not in pdfmetrics.getRegisteredFontNames():
            for name,file in [('HotelNoto','NotoSans-Regular.ttf'),('HotelNotoBold','NotoSans-Bold.ttf')]:pdfmetrics.registerFont(TTFont(name,str(FRONTEND_DIR/'static'/'fonts'/file)))
    result={name:ParagraphStyle(name,fontName=font,fontSize=size,leading=size*1.5,spaceAfter=8) for name,font,size in [('body','HotelNoto',9),('title','HotelNotoBold',18),('heading','HotelNotoBold',12)]}
    result['signature']=ParagraphStyle('signature',fontName='HotelNoto',fontSize=9,leading=14,alignment=1)
    return result

def cash(value):return f'{Decimal(value):,.2f} ₫'

def render(title,code,rows,summary,transactions=None):
    output=BytesIO();style=styles()
    def p(value,kind='body'):return Paragraph(escape(str(value)).replace('\n','<br/>'),style[kind])
    story=[p('LOTUS HOTEL - CHỨNG TỪ NỘI BỘ'),p(title,'title'),p(code),p('Không phải hóa đơn điện tử. Chỉ phản ánh giao dịch do nhân viên ghi nhận.'),Spacer(1,12)]
    data=[[p('Chi tiết'),p('Thành tiền / giá trị')]]+[[p(a),p(b)] for a,b in rows]
    table=Table(data,colWidths=[350,165],repeatRows=1,hAlign='LEFT')
    table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#eef1f7')),('LINEBELOW',(0,0),(-1,-1),.4,colors.HexColor('#dce1e9')),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),8),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
    story.extend([table,Spacer(1,16)])
    for label,value in summary:story.append(p(f'{label}: {value}','heading'))
    if transactions:
        story.extend([Spacer(1,12),p('Sổ thu / hoàn (tách khỏi chi phí)','heading')])
        for t in transactions:
            story.append(p(f"#{t['id']} - {t['kind']} / {t['method']} - {cash(t['amount'])}\n{t['at']} UTC - {t['actor']} - {t['reference']}"))
    signatures=Table([[p('Người lập / thu tiền','signature'),p('Khách xác nhận','signature')],[Spacer(1,40),Spacer(1,40)],[p('(Ký, ghi rõ họ tên)','signature'),p('(Ký, ghi rõ họ tên)','signature')]],colWidths=[257.5,257.5])
    story.extend([Spacer(1,20),KeepTogether([signatures])])
    def page(canvas,doc):
        canvas.setFont('HotelNoto',8);canvas.setFillColor(colors.HexColor('#667188'));canvas.drawString(40,25,'Lotus Hotel - Dữ liệu nội bộ');canvas.drawRightString(A4[0]-40,25,f'Trang {doc.page}')
    SimpleDocTemplate(output,pagesize=A4,leftMargin=40,rightMargin=40,topMargin=35,bottomMargin=45,title=title,author='Lotus Hotel').build(story,onFirstPage=page,onLaterPages=page)
    return output.getvalue()

def folio_pdf(folio):
    rows=[(item['description'],cash(item['amount'])) for item in folio['lines']]
    summary=[('Tổng phải trả',cash(folio['total'])),('Đã nhận / đã hoàn',cash(folio['received'])+' / '+cash(folio['refunded'])),('Còn phải thu (+) / có dư (-)',cash(folio['balance']))]
    if Decimal(folio['legacy_gap']):summary.append(('Chênh dữ liệu cũ cần đối chiếu',cash(folio['legacy_gap'])))
    return render('BẢNG KÊ LƯU TRÚ',folio['code']+' - '+folio['customer_name'],rows,summary,folio['transactions'])

def receipt_pdf(receipt):
    title='PHIẾU HOÀN TIỀN' if receipt['kind']=='refund' else 'SỐ DƯ LEGACY' if receipt['kind']=='legacy_opening' else 'PHIẾU THU CỌC' if receipt['kind']=='deposit' else 'PHIẾU THU'
    labels={'cash':'Tiền mặt','bank_transfer':'Chuyển khoản','unknown':'Không rõ (legacy)'}
    rows=[('Khách',receipt['customer_name']),('Phương thức',labels[receipt['method']]),('Người ghi',receipt['actor']),('Thời điểm UTC',receipt['at']),('Tham chiếu',receipt['reference'] or '-'),('Lý do',receipt['reason'] or '-')]
    if receipt['kind']=='legacy_opening':rows.append(('Lưu ý','Không biết ngày thu thực tế; không tính vào dòng tiền mới'))
    return render(title,f"#{receipt['id']} - {receipt['code']}",rows,[('Số tiền',cash(receipt['amount']))])
