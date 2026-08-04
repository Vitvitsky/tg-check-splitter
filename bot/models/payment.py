import uuid
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from bot.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    user_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    # SET NULL, not CASCADE: a payment is a financial record that must outlive the
    # session it was made for (deleting history must never erase money changing hands).
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True
    )
    stars_amount: Mapped[int] = mapped_column(Integer, nullable=False)
    # Unique: Telegram may redeliver a successful_payment update, and without this the
    # retry would be recorded as a second purchase and grant the scans twice.
    telegram_charge_id: Mapped[str] = mapped_column(String, nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
