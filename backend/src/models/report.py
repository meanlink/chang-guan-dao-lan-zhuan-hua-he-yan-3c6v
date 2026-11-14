from sqlalchemy import String, Double, ForeignKey, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class Report(Base):
    __tablename__ = 'reports'
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(160))
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.id'))
    destination: Mapped[str] = mapped_column(String(120))
    interval_seconds: Mapped[int]
    next_run: Mapped[float] = mapped_column(Double)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    # 撤回生效后置位：计划停发且不再随重新批准恢复，只能另建新计划
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked_reason: Mapped[str] = mapped_column(String(1000), default='')
    blocked_at: Mapped[float | None] = mapped_column(Double, nullable=True)
class Delivery(Base):
    __tablename__ = 'deliveries'
    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey('reports.id'))
    created_at: Mapped[float] = mapped_column(Double)
    checksum: Mapped[str] = mapped_column(String(64))
    filename: Mapped[str] = mapped_column(String(160))
    destination: Mapped[str] = mapped_column(String(120))
    # 旧归档留作审计但禁止下载；并发下晚完成的简报直接以拦截态落库，不进入可下载收件箱
    blocked: Mapped[bool] = mapped_column(Boolean, default=False)
    blocked_reason: Mapped[str] = mapped_column(String(1000), default='')
    blocked_at: Mapped[float | None] = mapped_column(Double, nullable=True)
