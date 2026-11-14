import time
from sqlalchemy import inspect, text
from src.config.database import Base, engine
from src import models


def _has_table(inspector, name):
    return name in inspector.get_table_names()


def _has_column(inspector, table, column):
    return column in {c['name'] for c in inspector.get_columns(table)}


def upgrade(engine):
    """幂等结构升级：全新库直接建表；旧库补列、补表并回填审批轨迹，原有关联保持不变。"""
    inspector = inspect(engine)
    real_columns = {
        'jobs': [('revoked_reason', "VARCHAR(1000) DEFAULT ''"),
                 ('revoked_at', 'DOUBLE PRECISION'),
                 ('revoked_by', "VARCHAR(150) DEFAULT ''")],
        'reports': [('blocked', 'BOOLEAN DEFAULT FALSE'),
                    ('blocked_reason', "VARCHAR(1000) DEFAULT ''"),
                    ('blocked_at', 'DOUBLE PRECISION')],
        'deliveries': [('blocked', 'BOOLEAN DEFAULT FALSE'),
                       ('blocked_reason', "VARCHAR(1000) DEFAULT ''"),
                       ('blocked_at', 'DOUBLE PRECISION')],
    }
    sqlite_types = {'DOUBLE PRECISION': 'FLOAT', 'BOOLEAN': 'BOOLEAN'}
    dialect = engine.dialect.name
    with engine.begin() as conn:
        for table, columns in real_columns.items():
            if not _has_table(inspector, table):
                continue
            for column, ddl_type in columns:
                if _has_column(inspector, table, column):
                    continue
                col_type = ddl_type
                if dialect == 'sqlite':
                    col_type = ' '.join(sqlite_types.get(part, part) for part in ddl_type.split())
                conn.execute(text(f'ALTER TABLE {table} ADD COLUMN {column} {col_type}'))
        # 审批轨迹表（旧库不存在时补建，结构与模型一致）
        if not _has_table(inspector, 'approvals'):
            models.Approval.__table__.create(bind=conn, checkfirst=True)
        # 旧数据迁移：已批准任务回填一条批准记录，保留原始任务关联；未批准任务不回填
        if _has_table(inspector, 'jobs'):
            backfilled = conn.execute(text(
                'SELECT j.id, j.created_by, u.email, j.finished_at, j.created_at '
                'FROM jobs j LEFT JOIN users u ON u.id = j.created_by '
                'WHERE j.approved = TRUE AND NOT EXISTS '
                '(SELECT 1 FROM approvals a WHERE a.job_id = j.id AND a.action = \'approve\')'
            )).mappings().all()
            for row in backfilled:
                conn.execute(text(
                    'INSERT INTO approvals (job_id, action, reason, actor, at) '
                    'VALUES (:job_id, :action, :reason, :actor, :at)'
                ), {'job_id': row['id'], 'action': 'approve', 'reason': '历史数据迁移回填',
                    'actor': row['email'] or 'migration',
                    'at': row['finished_at'] or row['created_at'] or time.time()})


def migrate():
    Base.metadata.create_all(engine)
    upgrade(engine)


if __name__ == '__main__':
    migrate()
