from sqlalchemy import String, Double, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from src.config.database import Base
class Approval(Base):
    """审批记录：批准与撤回均为不可变记录，重新批准另起一条。"""
    __tablename__ = 'approvals'
    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey('jobs.id'), index=True)
    action: Mapped[str] = mapped_column(String(20))  # approve / revoke
    reason: Mapped[str] = mapped_column(String(1000), default='')
    actor: Mapped[str] = mapped_column(String(150))
    at: Mapped[float] = mapped_column(Double, index=True)
