import logging

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import TelegramUser, get_current_user
from api.deps import get_db
from api.schemas import QuotaOut
from bot.config import get_settings
from bot.services.quota import QuotaService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/quota", tags=["quota"])


@router.get("", response_model=QuotaOut)
async def get_quota(
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuotaOut:
    logger.info("user_id=%s get quota", user.id)
    settings = get_settings()
    svc = QuotaService(db, settings.free_scans_per_month)
    free_left, paid, reset_at = await svc.get_quota_info(user.id)
    return QuotaOut(free_scans_left=free_left, paid_scans=paid, reset_at=reset_at)


@router.post("/reset", status_code=200)
async def reset_quota(
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reset free scan counter for the current user."""
    logger.info("user_id=%s reset quota", user.id)
    svc = QuotaService(db, get_settings().free_scans_per_month)
    quota = await svc._get_or_create(user.id)
    quota.free_scans_used = 0
    await db.commit()
    return {"ok": True}
