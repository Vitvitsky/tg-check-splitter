from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import TelegramUser, get_current_user
from api.deps import get_db
from api.schemas import QuotaOut
from bot.config import get_settings
from bot.services.quota import QuotaService

router = APIRouter(prefix="/api/quota", tags=["quota"])


@router.get("", response_model=QuotaOut)
async def get_quota(
    user: TelegramUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> QuotaOut:
    settings = get_settings()
    svc = QuotaService(db, settings.free_scans_per_month)
    free_left, paid, reset_at = await svc.get_quota_info(user.id)
    return QuotaOut(free_scans_left=free_left, paid_scans=paid, reset_at=reset_at)
