import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    Numeric,
    String,
    UniqueConstraint,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.models.base import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    admin_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    invite_code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="created", nullable=False)
    currency: Mapped[str] = mapped_column(String(8), default="RUB", nullable=False)
    tip_percent: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # cascade + passive_deletes: children go away with the session. The DB-level
    # ON DELETE CASCADE (see migration f1a2b3c4d5e6) does the actual work; the ORM
    # cascade keeps in-session state consistent without emitting per-row DELETEs.
    photos: Mapped[list["SessionPhoto"]] = relationship(
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    items: Mapped[list["SessionItem"]] = relationship(
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    members: Mapped[list["SessionMember"]] = relationship(
        back_populates="session",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class SessionPhoto(Base):
    __tablename__ = "session_photos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tg_file_id: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Receipt bytes, held only between upload and a successful OCR.
    #
    # They used to live in a process-local dict, which meant a restart orphaned every
    # in-flight session ("No photos available for OCR", unrecoverable) and the API could
    # never run more than one worker. Storing them here makes the bytes visible to any
    # process and, because session_id cascades, they are deleted with the session for
    # free — no sweeper, no TTL job, no disk budget.
    #
    # deferred: Session.photos is lazy="selectin", so without this EVERY session load
    # — every poll of GET /api/sessions/{id} — would drag megabytes of JPEG along.
    # Read it with an explicit select(SessionPhoto.data), never via the attribute.
    data: Mapped[bytes | None] = mapped_column(LargeBinary, nullable=True, deferred=True)

    session: Mapped["Session"] = relationship(back_populates="photos")


class SessionItem(Base):
    __tablename__ = "session_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    session: Mapped["Session"] = relationship(back_populates="items")
    votes: Mapped[list["ItemVote"]] = relationship(
        back_populates="item",
        lazy="selectin",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )


class SessionMember(Base):
    __tablename__ = "session_members"
    # One membership per user per session. Without this, two concurrent joins
    # (e.g. a double-tapped deep link) insert two rows and every later
    # get_member() raises MultipleResultsFound for that user, permanently.
    __table_args__ = (
        UniqueConstraint("session_id", "user_tg_id", name="uq_session_members_session_user"),
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    session_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    tip_percent: Mapped[int | None] = mapped_column(Integer, nullable=True, default=None)
    confirmed: Mapped[bool] = mapped_column(default=False, server_default="false", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    session: Mapped["Session"] = relationship(back_populates="members")


class ItemVote(Base):
    __tablename__ = "item_votes"
    # One vote row per user per item — see the note on SessionMember. A double tap
    # on the same dish used to create a second row and wedge cycle_vote() forever.
    __table_args__ = (UniqueConstraint("item_id", "user_tg_id", name="uq_item_votes_item_user"),)

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    item_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("session_items.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_tg_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1, server_default="1", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    item: Mapped["SessionItem"] = relationship(back_populates="votes")
