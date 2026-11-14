import time, os, csv, io, hashlib, json
from fastapi import HTTPException
from sqlalchemy import select
from src.models import Job, Report, Delivery
from src.config.settings import ARTIFACT_DIR


def _lock_row(db, model, row_id):
    """锁定计划/任务行；SQLite 不支持 FOR UPDATE，退化为普通读取。"""
    if db.bind.dialect.name == 'sqlite':
        return db.get(model, row_id)
    return db.scalars(select(model).where(model.id == row_id).with_for_update()).first()


def create(db, data):
    j = db.get(Job, data.job_id)
    if not j or j.status != 'completed' or not j.approved:
        raise HTTPException(409, '请先选择已完成且获批准的分析结果')
    r = Report(name=data.name, job_id=j.id, destination=data.destination,
               interval_seconds=data.interval_seconds,
               next_run=time.time() + data.delay_seconds, enabled=True)
    db.add(r); db.flush()
    return r


def deliver(db, report):
    """生成一次简报。撤回与分发并发时以行锁串行化（统一 Job→Report 锁序避免死锁）：
    - 任务批准已撤回：本次简报以拦截态落库（记录留痕），不写入可下载文件，不进入可下载收件箱；
    - 计划已被撤回拦截：不再生成任何文件。"""
    # 先锁任务行，与撤回事务保持相同锁序
    j = _lock_row(db, Job, report.job_id)
    r = _lock_row(db, Report, report.id)
    if not r or r.blocked:
        return None
    if not j or not j.approved:
        reason = (j.revoked_reason if j else '') or '关联结论批准已撤回'
        now = time.time()
        blocked = Delivery(report_id=r.id, created_at=now, checksum='', filename='',
                           destination=r.destination, blocked=True,
                           blocked_reason=reason, blocked_at=now)
        db.add(blocked); db.flush()
        r.enabled = False
        r.blocked = True
        r.blocked_reason = reason
        r.blocked_at = now
        record_blocked(db, r, blocked, reason)
        return blocked
    out = io.StringIO()
    out.write('﻿')
    table = j.result.get('table', {})
    cols = table.get('columns', [])
    writer = csv.writer(out)
    def safe(v):
        if isinstance(v, (int, float)) and not isinstance(v, bool): return v
        text = str(v)
        return "'" + text if text.startswith(('=', '+', '-', '@', '\t', '\r')) else text
    writer.writerow([safe(c['label']) for c in cols])
    for row in table.get('rows', []):
        writer.writerow([safe(row.get(c['key'], '')) for c in cols])
    data = out.getvalue().encode('utf-8')
    delivery = Delivery(report_id=r.id, created_at=time.time(),
                        checksum=hashlib.sha256(data).hexdigest(), filename='',
                        destination=r.destination)
    db.add(delivery); db.flush()
    delivery.filename = f'report-{r.id}-delivery-{delivery.id}.csv'
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    with open(os.path.join(ARTIFACT_DIR, delivery.filename), 'wb') as f:
        f.write(data)
    with open(os.path.join(ARTIFACT_DIR, delivery.filename + '.json'), 'w') as f:
        json.dump({'job': j.name, 'params': j.params, 'result': j.result,
                   'checksum': delivery.checksum}, f, ensure_ascii=False, allow_nan=False)
    r.next_run = time.time() + r.interval_seconds
    return delivery


def record_blocked(db, report, delivery, reason):
    from src.services.audit import record
    record(db, 'worker', 'report.blocked',
           {'id': report.id, 'delivery': delivery.id, 'reason': reason})
