import hashlib, json
def checksum(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False).encode()).hexdigest()
def dataset_dict(d):
    return {'id': d.id, 'name': d.name, 'source': d.source, 'rows': len(d.records),
            'checksum': d.checksum, 'created_at': d.created_at}
def job_dict(j):
    return {k: getattr(j, k) for k in ['id', 'name', 'dataset_id', 'params', 'status', 'result',
                                       'error', 'approved', 'revoked_reason', 'revoked_at',
                                       'revoked_by', 'created_at', 'finished_at']}
def report_dict(r):
    return {k: getattr(r, k) for k in ['id', 'name', 'job_id', 'destination', 'interval_seconds',
                                       'next_run', 'enabled', 'blocked', 'blocked_reason',
                                       'blocked_at']}
def delivery_dict(d):
    return {k: getattr(d, k) for k in ['id', 'report_id', 'created_at', 'checksum', 'filename',
                                       'destination', 'blocked', 'blocked_reason', 'blocked_at']}
def approval_dict(a):
    return {k: getattr(a, k) for k in ['id', 'job_id', 'action', 'reason', 'actor', 'at']}
