from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.base import Base


class UserQuota(Base):
    __tablename__ = "user_quotas"

    user_tg_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    free_scans_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    paid_scans: Mapped[int] = mapped_column(Integer, default=0, server_default="0", nullable=False)
    quota_reset_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
