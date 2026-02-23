"""Voting, tip, confirmation, and share-calculation routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import TelegramUser, get_current_user
from api.ws import (
    EVENT_MEMBER_CONFIRMED,
    EVENT_MEMBER_UNCONFIRMED,
    EVENT_TIP_CHANGED,
    EVENT_VOTE_UPDATED,
)
from api.deps import get_db
from api.schemas import ShareOut, TipIn, VoteIn
from bot.models.session import Session, SessionMember
from bot.services.calculator import calculate_shares, calculate_user_share
from bot.services.session import SessionService

router = APIRouter(tags=["voting"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _require_member(
    db: AsyncSession,
    session_id: str,
    user: TelegramUser,
) -> tuple[Session, SessionMember]:
    """Load the session and verify the user is a member.

    Returns the ``(session, member)`` pair or raises 404/403.
    """
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    member = await svc.get_member(session.id, user.id)
    if member is None:
        raise HTTPException(status_code=403, detail="Not a member of this session")
    return session, member


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/api/sessions/{session_id}/vote")
async def vote(
    session_id: str,
    body: VoteIn,
    request: Request,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cycle vote on an item (0 -> 1 -> 2 -> ... -> max -> 0)."""
    session, _member = await _require_member(db, session_id, user)

    # Find the item inside this session
    item = None
    for it in session.items:
        if str(it.id) == body.item_id:
            item = it
            break
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found in session")

    svc = SessionService(db)
    quantity, overflow_prevented = await svc.cycle_vote(
        item.id, user.id, item.quantity
    )

    manager = request.app.state.ws_manager
    await manager.broadcast(session_id, {
        "type": EVENT_VOTE_UPDATED,
        "data": {"item_id": body.item_id, "user_tg_id": user.id, "quantity": quantity},
    })

    return {"quantity": quantity, "overflow_prevented": overflow_prevented}


@router.post("/api/sessions/{session_id}/tip", status_code=200)
async def set_tip(
    session_id: str,
    body: TipIn,
    request: Request,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Set the current user's tip percentage for this session."""
    await _require_member(db, session_id, user)
    svc = SessionService(db)
    await svc.set_member_tip(session_id, user.id, body.tip_percent)

    manager = request.app.state.ws_manager
    await manager.broadcast(session_id, {
        "type": EVENT_TIP_CHANGED,
        "data": {"user_tg_id": user.id, "tip_percent": body.tip_percent},
    })

    return {"ok": True}


@router.post("/api/sessions/{session_id}/confirm", status_code=200)
async def confirm(
    session_id: str,
    request: Request,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Confirm the current user's selection."""
    await _require_member(db, session_id, user)
    svc = SessionService(db)
    await svc.confirm_member(session_id, user.id)

    manager = request.app.state.ws_manager
    await manager.broadcast(session_id, {
        "type": EVENT_MEMBER_CONFIRMED,
        "data": {"user_tg_id": user.id},
    })

    return {"ok": True}


@router.post("/api/sessions/{session_id}/unconfirm", status_code=200)
async def unconfirm(
    session_id: str,
    request: Request,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Undo the current user's confirmation."""
    await _require_member(db, session_id, user)
    svc = SessionService(db)
    await svc.unconfirm_member(session_id, user.id)

    manager = request.app.state.ws_manager
    await manager.broadcast(session_id, {
        "type": EVENT_MEMBER_UNCONFIRMED,
        "data": {"user_tg_id": user.id},
    })

    return {"ok": True}


@router.get("/api/sessions/{session_id}/shares", response_model=list[ShareOut])
async def get_shares(
    session_id: str,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all participant shares for the session."""
    session, _member = await _require_member(db, session_id, user)

    # Refresh items and their votes to avoid stale data
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
        m.user_tg_id: m.tip_percent
        for m in session.members
        if m.tip_percent is not None
    }

    shares = calculate_shares(
        items_data,
        tip_percent=session.tip_percent,
        per_person_tips=per_person_tips or None,
    )

    # Build display-name lookup
    name_by_tg_id = {m.user_tg_id: m.display_name for m in session.members}

    result: list[ShareOut] = []
    for tg_id, grand_total in shares.items():
        # Compute per-user breakdown
        tip_pct = (
            per_person_tips.get(tg_id, session.tip_percent)
            if per_person_tips
            else session.tip_percent
        )
        dishes_total, tip_amount, _ = calculate_user_share(
            items_data, tg_id, tip_pct
        )
        result.append(
            ShareOut(
                user_tg_id=tg_id,
                display_name=name_by_tg_id.get(tg_id, "Unknown"),
                dishes_total=float(dishes_total),
                tip_amount=float(tip_amount),
                grand_total=float(grand_total),
            )
        )

    return result


@router.get("/api/sessions/{session_id}/my-share", response_model=ShareOut)
async def get_my_share(
    session_id: str,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get the current user's share breakdown."""
    session, member = await _require_member(db, session_id, user)

    # Refresh items and their votes to avoid stale data
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

    tip_pct = member.tip_percent if member.tip_percent is not None else session.tip_percent

    dishes_total, tip_amount, grand_total = calculate_user_share(
        items_data, user.id, tip_pct
    )

    # Build display-name lookup
    name_by_tg_id = {m.user_tg_id: m.display_name for m in session.members}

    return ShareOut(
        user_tg_id=user.id,
        display_name=name_by_tg_id.get(user.id, "Unknown"),
        dishes_total=float(dishes_total),
        tip_amount=float(tip_amount),
        grand_total=float(grand_total),
    )
