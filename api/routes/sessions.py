"""Session CRUD REST routes."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import TelegramUser, get_current_user
from api.ws import EVENT_MEMBER_JOINED, EVENT_SESSION_STATUS
from api.deps import get_db
from api.schemas import (
    MemberOut,
    SessionBrief,
    SessionCreateIn,
    SessionOut,
    ShareOut,
)
from api.services.notifications import NotificationService
from bot.config import get_settings
from bot.models.session import SessionMember
from bot.services.calculator import calculate_shares, calculate_user_share
from bot.services.session import SessionService

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_admin(session, user: TelegramUser) -> None:
    if session.admin_tg_id != user.id:
        raise HTTPException(403, "Admin access required")


def _require_member(session, user: TelegramUser) -> None:
    if user.id not in {m.user_tg_id for m in session.members}:
        raise HTTPException(403, "Not a session member")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("", status_code=201, response_model=SessionOut)
async def create_session(
    body: SessionCreateIn,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SessionService(db)
    session = await svc.create_session(user.id, user.first_name)
    await svc.update_currency(session.id, body.currency)
    # Refresh to pick up updated currency
    await db.refresh(session)
    return session


@router.get("/my", response_model=list[SessionBrief])
async def my_sessions(
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(SessionMember).where(SessionMember.user_tg_id == user.id))
    memberships = result.scalars().all()

    briefs: list[SessionBrief] = []
    for membership in memberships:
        # Load the related session via the service
        svc = SessionService(db)
        session = await svc.get_session_by_id(membership.session_id)
        if session is None:
            continue
        briefs.append(
            SessionBrief(
                id=str(session.id),
                invite_code=session.invite_code,
                status=session.status,
                created_at=session.created_at,
                member_count=len(session.members),
                item_count=len(session.items),
            )
        )
    return briefs


@router.get("/invite/{invite_code}", response_model=SessionOut)
async def get_session_by_invite(
    invite_code: str,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SessionService(db)
    session = await svc.get_session_by_invite(invite_code)
    if session is None:
        raise HTTPException(404, "Session not found")
    return session


@router.get("/{session_id}", response_model=SessionOut)
async def get_session(
    session_id: UUID,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    _require_member(session, user)
    return session


@router.post("/invite/{invite_code}/join", status_code=201, response_model=MemberOut)
async def join_session(
    invite_code: str,
    request: Request,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SessionService(db)
    # First check if the session exists
    session = await svc.get_session_by_invite(invite_code)
    if session is None:
        raise HTTPException(404, "Session not found")

    # Check if user is already a member
    existing = await svc.get_member(session.id, user.id)
    if existing is not None:
        raise HTTPException(409, "Already a session member")

    member = await svc.join_session(invite_code, user.id, user.first_name)
    # member should not be None here since we already checked above

    manager = request.app.state.ws_manager
    await manager.broadcast(
        str(session.id),
        {
            "type": EVENT_MEMBER_JOINED,
            "data": {"user_tg_id": user.id, "display_name": user.first_name},
        },
    )

    # Send push notification to admin
    settings = get_settings()
    notifier = NotificationService(settings.bot_token)
    await notifier.notify_member_joined(session.admin_tg_id, user.first_name)

    return member


@router.post("/{session_id}/finish", status_code=200)
async def finish_voting(
    session_id: UUID,
    request: Request,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    _require_admin(session, user)
    await svc.update_status(session_id, "closed")

    manager = request.app.state.ws_manager
    await manager.broadcast(
        str(session_id),
        {
            "type": EVENT_SESSION_STATUS,
            "data": {"status": "closed"},
        },
    )

    return {"status": "closed"}


@router.post("/{session_id}/settle", response_model=list[ShareOut])
async def settle_session(
    session_id: UUID,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(404, "Session not found")
    _require_admin(session, user)

    # Refresh relationships to ensure items/votes/members are up-to-date
    await db.refresh(session, ["items", "members"])
    for item in session.items:
        await db.refresh(item, ["votes"])

    items_data = [
        {
            "price": item.price,
            "quantity": item.quantity,
            "votes": {v.user_tg_id: v.quantity for v in item.votes},
        }
        for item in session.items
    ]
    per_person_tips = {
        m.user_tg_id: m.tip_percent for m in session.members if m.tip_percent is not None
    }
    shares = calculate_shares(items_data, session.tip_percent, per_person_tips)

    # Build display-name lookup
    name_map = {m.user_tg_id: m.display_name for m in session.members}

    await svc.update_status(session_id, "settled")

    result: list[ShareOut] = []
    for uid, grand_total in shares.items():
        # Recompute per-user breakdown for the response
        tip = per_person_tips.get(uid, session.tip_percent)
        dishes_total, tip_amount, _ = calculate_user_share(items_data, uid, tip)
        result.append(
            ShareOut(
                user_tg_id=uid,
                display_name=name_map.get(uid, "Unknown"),
                dishes_total=float(dishes_total),
                tip_amount=float(tip_amount),
                grand_total=float(grand_total),
            )
        )

    # Send push notifications to all members
    settings = get_settings()
    notifier = NotificationService(settings.bot_token)
    members_data = [
        {"user_tg_id": m.user_tg_id, "display_name": m.display_name} for m in session.members
    ]
    await notifier.notify_settle(
        members_data,
        shares,
        session.currency or "RUB",
        settings.webapp_url,
        session.invite_code,
    )

    return result
