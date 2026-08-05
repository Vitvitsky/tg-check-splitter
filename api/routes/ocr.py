"""OCR and item management routes."""

import asyncio
import logging
from decimal import Decimal
from uuid import UUID, uuid4

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import TelegramUser, get_current_user
from api.deps import get_db
from api.schemas import (
    ItemOut,
    ItemsUpdateIn,
    ItemUpdateIn,
    OcrItemOut,
    OcrResultOut,
    PhotoOut,
)
from api.ws import EVENT_ITEMS_UPDATED, EVENT_OCR_PROGRESS
from core.config import get_settings
from core.models.session import Session
from core.services.ocr import OcrService
from core.services.quota import QuotaService
from core.services.session import SessionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions/{session_id}", tags=["ocr"])

_MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB

# Photos per receipt. Bounds both the OCR bill and the in-memory photo store, and keeps
# the worst-case recognition time inside the deadline below.
_MAX_PHOTOS = 5

# Hard ceiling on one OCR request, deliberately under nginx's proxy_read_timeout (300 s
# in nginx/tg-check-splitter.conf). Exceeding that timeout produced a 504 from nginx
# *after* the scan had been charged, with nothing left to refund it — the request was
# already gone. Failing here instead keeps the refund path reachable.
_OCR_DEADLINE_SECONDS = 240


async def _get_session_require_admin(
    session_id: str, user: TelegramUser, db: AsyncSession, *, must_be_open: bool = True
) -> Session:
    """Load a session for an admin-only operation.

    ``must_be_open`` rejects a settled session: once everyone has been told what they
    owe, changing the receipt would move the amounts out from under them. It is also
    what keeps POST /settle idempotent — the shares are recomputed on demand, so they
    only stay stable while the inputs cannot change.
    """
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.admin_tg_id != user.id:
        raise HTTPException(403, "Admin access required")
    if must_be_open and session.status == "settled":
        raise HTTPException(409, "session_settled")
    return session


@router.post("/photos", response_model=list[PhotoOut], status_code=201)
async def upload_photos(
    session_id: str,
    request: Request,
    files: list[UploadFile],
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[PhotoOut]:
    """Upload receipt photos for a session (admin only)."""
    logger.info("user_id=%s upload photos session=%s count=%d", user.id, session_id, len(files))
    session = await _get_session_require_admin(session_id, user, db)
    svc = SessionService(db)

    # Cap the total, not just this batch — uploads are incremental. Rejecting here keeps
    # the OCR limit from becoming a dead end where a session can be filled with photos
    # that can never be recognised.
    already = len(session.photos)
    if already + len(files) > _MAX_PHOTOS:
        raise HTTPException(
            400,
            detail=(f"A receipt takes at most {_MAX_PHOTOS} photos ({already} already uploaded)."),
        )

    photos_out: list[PhotoOut] = []
    for f in files:
        data = await f.read()
        if len(data) > _MAX_PHOTO_SIZE:
            raise HTTPException(413, f"File {f.filename} exceeds 5 MB limit")

        # Bytes go on the row, not into a process-local dict: see the migration
        # a7c3e91b40d2 for why. tg_file_id stays a synthetic id — the column is NOT NULL
        # and predates Mini App uploads, when it held a real Telegram file id.
        photo = await svc.add_photo(session_id, f"miniapp-{uuid4()}", data=data)
        photos_out.append(PhotoOut.model_validate(photo))

    return photos_out


@router.post("/ocr", response_model=OcrResultOut)
async def trigger_ocr(
    session_id: str,
    request: Request,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> OcrResultOut:
    """Trigger OCR on uploaded photos (admin only)."""
    logger.info("user_id=%s OCR trigger session=%s", user.id, session_id)
    # Authorization only — the photos are read below by explicit query, not off the
    # session's (deferred) relationship.
    await _get_session_require_admin(session_id, user, db)
    svc = SessionService(db)
    settings = get_settings()

    # Collect the photos BEFORE charging. This used to run after the scan was consumed,
    # so a session with no usable bytes answered 400 and still cost the user a scan.
    #
    # Explicit select rather than photo.data: the column is deferred precisely so that
    # ordinary session reads do not carry the JPEGs, and touching the attribute would
    # emit a lazy load per photo (and raise MissingGreenlet in async context).
    photos_bytes = await svc.get_photo_bytes(session_id)

    if not photos_bytes:
        raise HTTPException(400, detail="No photos available for OCR. Try uploading again.")
    if len(photos_bytes) > _MAX_PHOTOS:
        raise HTTPException(
            400,
            detail=f"Too many photos ({len(photos_bytes)}); {_MAX_PHOTOS} is the maximum.",
        )

    quota_svc = QuotaService(db, settings.free_scans_per_month)
    charged = await quota_svc.use_scan(user.id)
    if charged is None:
        raise HTTPException(402, detail="quota_exhausted")

    manager = request.app.state.ws_manager
    total_photos = len(photos_bytes)

    async def report_progress(completed: int, total: int) -> None:
        await manager.broadcast(
            session_id,
            {"type": EVENT_OCR_PROGRESS, "data": {"current": completed, "total": total}},
        )

    if total_photos > 1:
        await report_progress(0, total_photos)

    ocr_service = OcrService(settings.zai_api_key, settings.zai_model)

    # Every exit from here that does not produce items refunds the scan: the user is
    # charged for a parsed receipt, not for an attempt.
    try:
        async with asyncio.timeout(_OCR_DEADLINE_SECONDS):
            result = await ocr_service.parse_receipt(photos_bytes, on_progress=report_progress)
    except TimeoutError:
        await quota_svc.refund_scan(user.id, charged)
        logger.error("OCR timed out after %ss (%d photos)", _OCR_DEADLINE_SECONDS, total_photos)
        raise HTTPException(504, detail="Recognition took too long. Try fewer photos.")
    except httpx.HTTPError as exc:
        await quota_svc.refund_scan(user.id, charged)
        logger.error("OCR provider error: %s", exc)
        raise HTTPException(502, detail="Recognition service is unavailable. Try again.")
    except ValueError as exc:
        await quota_svc.refund_scan(user.id, charged)
        logger.error("OCR failed: %s", exc)
        raise HTTPException(422, detail="Could not parse receipt. Try a clearer photo.")

    if not result.items:
        await quota_svc.refund_scan(user.id, charged)
        raise HTTPException(422, detail="No items found on the receipt. Try a clearer photo.")

    await svc.save_ocr_items(
        session_id,
        [{"name": i.name, "price": float(i.price), "quantity": i.quantity} for i in result.items],
    )

    if result.currency:
        await svc.update_currency(session_id, result.currency)

    # The receipt has been read; the bytes have no further use. Dropping them here is
    # what keeps steady-state storage at roughly zero — the cascade on session delete is
    # only the backstop for sessions that never got this far.
    await svc.clear_photo_bytes(session_id)

    return OcrResultOut(
        items=[
            OcrItemOut(name=i.name, price=float(i.price), quantity=i.quantity)
            for i in result.items
        ],
        total=float(result.total),
        currency=result.currency,
        total_mismatch=result.total_mismatch,
    )


@router.put("/items", response_model=list[ItemOut])
async def replace_all_items(
    session_id: str,
    body: ItemsUpdateIn,
    request: Request,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[ItemOut]:
    """Replace all items in a session (admin only)."""
    logger.info(
        "user_id=%s replace items session=%s count=%d", user.id, session_id, len(body.items)
    )
    await _get_session_require_admin(session_id, user, db)
    svc = SessionService(db)

    await svc.clear_items(session_id)
    items = await svc.save_ocr_items(session_id, [item.model_dump() for item in body.items])

    manager = request.app.state.ws_manager
    await manager.broadcast(
        session_id,
        {
            "type": EVENT_ITEMS_UPDATED,
            "data": {"count": len(items)},
        },
    )

    return [ItemOut.model_validate(item) for item in items]


@router.put("/items/{item_id}", status_code=200)
async def update_single_item(
    session_id: str,
    item_id: str,
    body: ItemUpdateIn,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Update a single item (admin only)."""
    logger.info("user_id=%s update item=%s session=%s", user.id, item_id, session_id)
    await _get_session_require_admin(session_id, user, db)
    svc = SessionService(db)
    await svc.update_item(UUID(item_id), body.name, Decimal(str(body.price)))
    return {"ok": True}


@router.delete("/items/{item_id}", status_code=204)
async def delete_item(
    session_id: str,
    item_id: str,
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a single item (admin only)."""
    logger.info("user_id=%s delete item=%s session=%s", user.id, item_id, session_id)
    await _get_session_require_admin(session_id, user, db)
    svc = SessionService(db)
    await svc.delete_item(UUID(item_id))
