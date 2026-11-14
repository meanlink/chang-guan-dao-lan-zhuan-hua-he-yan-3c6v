from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from src.config.database import get_db
from src.models import Job, Approval
from src.schemas.job import JobInput
from src.schemas.approval import RevokeInput
from src.middlewares.auth import current_user, can_write, admin_only
from src.services import jobs, approvals
from src.services.audit import record
from src.utils.serialization import job_dict, approval_dict
router = APIRouter(prefix='/jobs')
@router.get('')
def listing(db=Depends(get_db), u=Depends(current_user)):
    return [job_dict(j) for j in db.scalars(select(Job).order_by(Job.id.desc()).limit(100))]
@router.post('', status_code=201)
def create(data: JobInput, db=Depends(get_db), u=Depends(can_write)):
    j = jobs.create(db, data, u); record(db, u.email, 'job.create', {'id': j.id, 'params': j.params})
    db.commit(); jobs.enqueue(j.id); return job_dict(j)
@router.get('/{id}')
def detail(id: int, db=Depends(get_db), u=Depends(current_user)):
    j = db.get(Job, id)
    if not j: raise HTTPException(404, '分析任务不存在')
    return job_dict(j)
@router.get('/{id}/approvals')
def approval_trail(id: int, db=Depends(get_db), u=Depends(current_user)):
    j = db.get(Job, id)
    if not j: raise HTTPException(404, '分析任务不存在')
    rows = db.scalars(select(Approval).where(Approval.job_id == id).order_by(Approval.id.asc()))
    return [approval_dict(a) for a in rows]
@router.post('/{id}/approve')
def approve(id: int, db=Depends(get_db), u=Depends(admin_only)):
    j = approvals.approve(db, id, u); db.commit()
    return job_dict(j)
@router.post('/{id}/revoke')
def revoke(id: int, data: RevokeInput, db=Depends(get_db), u=Depends(admin_only)):
    j = approvals.revoke(db, id, data.reason, u); db.commit()
    return job_dict(j)
