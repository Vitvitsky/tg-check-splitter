"""OCR and item management routes."""

import logging
from decimal import Decimal
from uuid import UUID, uuid4

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
from bot.config import get_settings
from bot.models.session import Session
from bot.services.ocr import OcrService
from bot.services.quota import QuotaService
from bot.services.session import SessionService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/sessions/{session_id}", tags=["ocr"])

_MAX_PHOTO_SIZE = 5 * 1024 * 1024  # 5 MB


async def _get_session_require_admin(
    session_id: str, user: TelegramUser, db: AsyncSession
) -> Session:
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    if not session:
        raise HTTPException(404, "Session not found")
    if session.admin_tg_id != user.id:
        raise HTTPException(403, "Admin access required")
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
    await _get_session_require_admin(session_id, user, db)
    svc = SessionService(db)

    if not hasattr(request.app.state, "photo_storage"):
        request.app.state.photo_storage = {}

    photos_out: list[PhotoOut] = []
    for f in files:
        data = await f.read()
        if len(data) > _MAX_PHOTO_SIZE:
            raise HTTPException(413, f"File {f.filename} exceeds 5 MB limit")

        placeholder_id = f"miniapp-{uuid4()}"
        request.app.state.photo_storage[placeholder_id] = data

        photo = await svc.add_photo(session_id, placeholder_id)
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
    session = await _get_session_require_admin(session_id, user, db)
    svc = SessionService(db)

    settings = get_settings()
    quota_svc = QuotaService(db, settings.free_scans_per_month)
    if not await quota_svc.can_scan(user.id):
        raise HTTPException(
            402,
            detail="quota_exhausted",
        )
    used = await quota_svc.use_scan(user.id)
    if not used:
        raise HTTPException(402, detail="quota_exhausted")

    if not hasattr(request.app.state, "photo_storage"):
        request.app.state.photo_storage = {}

    photos_bytes: list[bytes] = []
    for photo in session.photos:
        raw = request.app.state.photo_storage.get(photo.tg_file_id)
        if raw:
            photos_bytes.append(raw)

    if not photos_bytes:
        raise HTTPException(
            400,
            detail="No photos available for OCR. Try uploading again.",
        )

    ocr_service = OcrService(settings.openrouter_api_key, settings.openrouter_model)

    # Send OCR progress via WebSocket for multi-photo receipts
    manager = request.app.state.ws_manager
    total_photos = len(photos_bytes)
    if total_photos > 1:
        await manager.broadcast(session_id, {
            "type": EVENT_OCR_PROGRESS,
            "data": {"current": 0, "total": total_photos},
        })

        results = []
        for i, photo in enumerate(photos_bytes):
            single = await ocr_service._parse_single_photo(photo)
            results.append(single)
            await manager.broadcast(session_id, {
                "type": EVENT_OCR_PROGRESS,
                "data": {"current": i + 1, "total": total_photos},
            })
        result = ocr_service._merge_results(results)
    else:
        result = await ocr_service.parse_receipt(photos_bytes)

    await svc.save_ocr_items(
        session_id,
        [{"name": i.name, "price": float(i.price), "quantity": i.quantity} for i in result.items],
    )

    if result.currency:
        await svc.update_currency(session_id, result.currency)

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
    logger.info("user_id=%s replace items session=%s count=%d", user.id, session_id, len(body.items))
    await _get_session_require_admin(session_id, user, db)
    svc = SessionService(db)

    await svc.clear_items(session_id)
    items = await svc.save_ocr_items(session_id, [item.model_dump() for item in body.items])

    manager = request.app.state.ws_manager
    await manager.broadcast(session_id, {
        "type": EVENT_ITEMS_UPDATED,
        "data": {"count": len(items)},
    })

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
