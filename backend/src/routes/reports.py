import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy import select
from src.config.database import get_db
from src.config.settings import ARTIFACT_DIR
from src.models import Report, Delivery
from src.schemas.report import ReportInput
from src.middlewares.auth import current_user, admin_only
from src.services import reports
from src.services.audit import record
from src.utils.serialization import report_dict, delivery_dict
router = APIRouter()
@router.get('/reports')
def listing(db=Depends(get_db), u=Depends(current_user)):
    return [report_dict(r) for r in db.scalars(select(Report).order_by(Report.id.desc()))]
@router.post('/reports', status_code=201)
def create(data: ReportInput, db=Depends(get_db), u=Depends(admin_only)):
    r = reports.create(db, data)
    record(db, u.email, 'report.schedule', {'id': r.id, 'destination': r.destination})
    db.commit()
    return report_dict(r)
@router.post('/reports/{id}/toggle')
def toggle(id: int, db=Depends(get_db), u=Depends(admin_only)):
    r = db.get(Report, id)
    if not r: raise HTTPException(404, '分发计划不存在')
    if r.blocked: raise HTTPException(409, '计划已被撤回拦截并停发，重新批准不会恢复，请另建分发计划')
    r.enabled = not r.enabled
    record(db, u.email, 'report.toggle', {'id': id, 'enabled': r.enabled}); db.commit()
    return report_dict(r)
@router.get('/deliveries')
def deliveries(db=Depends(get_db), u=Depends(current_user)):
    items = []
    for d in db.scalars(select(Delivery).order_by(Delivery.id.desc()).limit(100)):
        item = delivery_dict(d)
        # 纵深防御：并发快照下即使归档标记未及更新，所属计划已拦截也不得呈现为可下载
        report = db.get(Report, d.report_id)
        if report and report.blocked and not item['blocked']:
            item['blocked'] = True
            item['blocked_reason'] = item['blocked_reason'] or report.blocked_reason
            item['blocked_at'] = item['blocked_at'] or report.blocked_at
        items.append(item)
    return items
@router.get('/deliveries/{id}/download')
def download(id: int, format: str = 'csv', db=Depends(get_db), u=Depends(current_user)):
    d = db.get(Delivery, id)
    if not d: raise HTTPException(404, '归档不存在')
    report = db.get(Report, d.report_id)
    if d.blocked or (report is not None and report.blocked):
        raise HTTPException(409, '该归档已随结论撤回停止下载，仅保留审计记录')
    if format not in ('csv', 'json'): raise HTTPException(422, '支持 CSV 或 JSON')
    filename = d.filename + ('.json' if format == 'json' else '')
    p = os.path.join(ARTIFACT_DIR, filename)
    if not os.path.exists(p): raise HTTPException(404, '归档文件不存在，请重新安排分发')
    return FileResponse(p, filename=filename,
                        media_type='application/json' if format == 'json' else 'text/csv; charset=utf-8')
