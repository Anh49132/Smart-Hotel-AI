"""Gemini selects verified metrics and bounded promotion ideas, never invents numbers."""
import json
from typing import Literal
from pydantic import BaseModel,ConfigDict,Field,ValidationError
from fastapi import HTTPException
from sqlalchemy import select
from backend.models import CashierShift,Role
from .reports_service import operating_report
from .shifts_service import shift_view
from .gemini_client import generate_structured

REPORT_VERSION='operating-report-v2'
SYSTEM='''Bạn là trợ lý phân tích khách sạn. Chọn các chỉ số quan trọng từ metrics, sao chép chính xác key và value. Không tính lại, không bịa số liệu. Chỉ đề xuất promotion_codes trong schema; đây là ý tưởng để quản lý cân nhắc, không phải thay đổi giá. Trả JSON đúng schema, không có văn bản khác.'''
LABELS={'occupancy':'Công suất theo lịch (%)','allocated_nights':'Đêm phòng phân bổ','invoice_net':'Doanh thu hóa đơn ròng trong kỳ (₫)','net_cash':'Thu tiền ròng trong kỳ (₫)','refunded':'Hoàn tiền trong kỳ (₫)','receivables_now':'Công nợ hiện tại (₫)'}
PROMOTIONS={'weekday':'Cân nhắc ưu đãi ngày thường sau khi kiểm tra lịch còn trống và biên lợi nhuận.','long_stay':'Cân nhắc gói ở dài ngày; quản lý cần duyệt giá và điều kiện áp dụng.','service_bundle':'Cân nhắc gói phòng kèm dịch vụ đang bán, kiểm tra chi phí trước khi công bố.'}

class Metric(BaseModel):
    model_config=ConfigDict(extra='forbid')
    key:Literal['occupancy','allocated_nights','invoice_net','net_cash','refunded','receivables_now']
    value:str

class ReportSelection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    highlights:list[Metric]=Field(min_length=1,max_length=6)
    promotion_codes:list[Literal['weekday','long_stay','service_bundle']]=Field(max_length=3)

async def draft_report(db,start,end):
    report=operating_report(db,start,end)
    metrics={k:str(report[k]) for k in LABELS}
    source={'start':str(start),'end_exclusive':str(end),'metrics':metrics,'basis':'UTC+7; công suất theo lịch; công nợ hiện tại; hóa đơn và dòng tiền có mốc riêng'}
    db.rollback()
    raw=await generate_structured(json.dumps(source,ensure_ascii=False),SYSTEM,ReportSelection.model_json_schema())
    try:result=ReportSelection.model_validate_json(raw)
    except ValidationError:raise HTTPException(502,'Báo cáo AI sai cấu trúc; hãy thử lại') from None
    if len({i.key for i in result.highlights})!=len(result.highlights):raise HTTPException(502,'AI lặp chỉ số')
    for item in result.highlights:
        if item.value!=metrics[item.key]:raise HTTPException(502,'Số liệu AI không khớp nguồn đã kiểm chứng')
    lines=[f'Báo cáo {start} đến trước {end} (UTC+7)',source['basis']]
    lines += [f'{LABELS[i.key]}: {i.value}' for i in result.highlights]
    lines += ['Gợi ý cần quản lý duyệt: '+PROMOTIONS[c] for c in dict.fromkeys(result.promotion_codes)]
    lines.append('Ảnh chụp dữ liệu tại lúc yêu cầu, có thể thay đổi sau đó. Không tự áp dụng khuyến mại.')
    return '\n\n'.join(lines),source

class HandoverSelection(BaseModel):
    model_config=ConfigDict(extra='forbid')
    focus:list[Literal['cash','transfer','difference','pending']]=Field(min_length=1,max_length=4)

async def draft_handover(db,shift_id,user):
    shift=db.get(CashierShift,shift_id)
    if not shift:raise HTTPException(404,'Không tìm thấy ca')
    if user.role!=Role.admin and shift.cashier_id!=user.id:raise HTTPException(403,'Chỉ tóm tắt ca của chính mình')
    view=shift_view(db,shift)
    # Never send handover notes, staff names, transaction references or guest data.
    source={'shift_id':shift.id,'status':shift.status,'opening_cash':str(shift.opening_cash),'counted_cash':str(shift.counted_cash),'difference':str(shift.difference),'totals':view['totals']}
    raw=await generate_structured(json.dumps(source,default=str), 'Chọn các mục cần nhấn mạnh từ dữ liệu ca bằng focus trong schema. Không thêm nội dung khác.',HandoverSelection.model_json_schema())
    try:result=HandoverSelection.model_validate_json(raw)
    except ValidationError:raise HTTPException(502,'Tóm tắt ca sai cấu trúc') from None
    facts={'cash':f"Tiền mặt thu/hoàn: {view['totals']['cash']['in']} / {view['totals']['cash']['out']} ₫; két dự kiến {view['totals']['expected_cash']} ₫",'transfer':f"Chuyển khoản thu/hoàn: {view['totals']['bank_transfer']['in']} / {view['totals']['bank_transfer']['out']} ₫",'difference':f"Chênh kiểm đếm: {shift.difference if shift.status=='closed' else 'Chưa chốt ca'}",'pending':f"Việc tồn lúc chốt: {json.dumps(view['totals'].get('pending',{}),ensure_ascii=False)}"}
    return f'Ca #{shift.id} · {shift.status}\n\n'+'\n\n'.join(facts[k] for k in dict.fromkeys(result.focus)),json.loads(json.dumps(source,default=str))
