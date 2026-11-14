import time
from fastapi import HTTPException
from sqlalchemy import select
from src.models import Job, Report, Delivery, Approval
from src.services.audit import record


def _lock_job(db, job_id):
    """锁定任务行。PostgreSQL 走 FOR UPDATE 串行化撤回/分发并发；SQLite 不支持该子句，退化为普通读取。"""
    if db.bind.dialect.name == 'sqlite':
        return db.get(Job, job_id)
    return db.scalars(select(Job).where(Job.id == job_id).with_for_update()).first()


def approve(db, job_id, user):
    """重新批准产生新审批记录；被撤回拦截的旧计划与旧归档不随之恢复。"""
    j = _lock_job(db, job_id)
    if not j:
        raise HTTPException(404, '分析任务不存在')
    if j.status != 'completed':
        raise HTTPException(409, '仅已完成结果可以批准')
    if j.approved:
        raise HTTPException(409, '该结论已处于批准状态，无需重复批准')
    j.approved = True
    j.revoked_reason = ''
    j.revoked_at = None
    j.revoked_by = ''
    entry = Approval(job_id=j.id, action='approve', reason='', actor=user.email, at=time.time())
    db.add(entry); db.flush()
    record(db, user.email, 'job.approve', {'id': j.id, 'approval_id': entry.id})
    return j


def revoke(db, job_id, reason, user):
    """撤回批准（单事务）：
    1. 任务回到未批准并记录撤回原因；
    2. 关联计划置拦截态停发，且不会因重新批准恢复；
    3. 旧归档保留审计可见但禁止下载；
    4. 审批轨迹新增不可变撤回记录。
    未处于批准状态时返回 409，调用方安全重试不会产生重复记账。"""
    reason = (reason or '').strip()
    if not reason:
        raise HTTPException(422, '撤回必须填写原因')
    if len(reason) > 1000:
        raise HTTPException(422, '撤回原因不能超过 1000 字')
    j = _lock_job(db, job_id)
    if not j:
        raise HTTPException(404, '分析任务不存在')
    if not j.approved:
        raise HTTPException(409, '该结论未处于批准状态，无法撤回（重复请求未产生任何记录）')
    now = time.time()
    actor = user.email
    j.approved = False
    j.revoked_reason = reason
    j.revoked_at = now
    j.revoked_by = actor
    blocked_reports = 0
    blocked_deliveries = 0
    for r in db.scalars(select(Report).where(Report.job_id == j.id, Report.blocked == False)):  # noqa: E712
        r.enabled = False
        r.blocked = True
        r.blocked_reason = reason
        r.blocked_at = now
        blocked_reports += 1
        for d in db.scalars(select(Delivery).where(Delivery.report_id == r.id, Delivery.blocked == False)):  # noqa: E712
            d.blocked = True
            d.blocked_reason = reason
            d.blocked_at = now
            blocked_deliveries += 1
    db.add(Approval(job_id=j.id, action='revoke', reason=reason, actor=actor, at=now))
    db.flush()
    record(db, actor, 'job.revoke',
           {'id': j.id, 'reason': reason, 'blocked_reports': blocked_reports,
            'blocked_deliveries': blocked_deliveries})
    return j
