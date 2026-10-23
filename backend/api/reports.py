from datetime import date
from fastapi import APIRouter,Depends
from fastapi.responses import Response
from backend.dependencies import require_roles
from backend.models import Role
from backend.services.reports_service import operating_report,report_csv
from core.database import get_db

router=APIRouter(prefix='/reports')
finance=require_roles(Role.admin,Role.accountant)

@router.get('/operations')
def operations(start:date,end:date,db=Depends(get_db),user=Depends(finance)):
    return operating_report(db,start,end)

@router.get('/operations.csv')
def export_operations(start:date,end:date,db=Depends(get_db),user=Depends(finance)):
    return Response(report_csv(operating_report(db,start,end)),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="hotel-operations.csv"','Cache-Control':'no-store'})
