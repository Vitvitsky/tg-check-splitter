import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from api.auth import TelegramUser, get_current_user
from api.deps import get_db
from api.schemas import InvoiceIn, InvoiceOut, QuotaOut
from api.services.notifications import NotificationService
from bot.config import get_settings
from bot.services.quota import QuotaService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/quota", tags=["quota"])

# Purchasable bundles. Prices live here, not in the request: the client must not be
# able to name its own price for a pack of scans.
SCAN_PACKS: dict[int, int] = {5: 50, 20: 150}  # scans -> Stars


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


@router.post("/invoice", response_model=InvoiceOut)
async def create_invoice(
    body: InvoiceIn,
    user: TelegramUser = Depends(get_current_user),
) -> InvoiceOut:
    """Create a Telegram Stars invoice link for a pack of scans.

    The Mini App opens the returned link with ``openInvoice()``. Crediting happens in
    bot/handlers/payment.py, which is where Telegram delivers the payment updates.
    """
    stars = SCAN_PACKS.get(body.scans)
    if stars is None:
        raise HTTPException(400, f"Unknown pack: {body.scans} scans")

    logger.info("user_id=%s invoice scans=%d stars=%d", user.id, body.scans, stars)
    notifier = NotificationService(get_settings().bot_token)
    link = await notifier.create_invoice_link(
        title=f"{body.scans} scans",
        description=f"{body.scans} receipt scans for Check Splitter",
        payload=f"scans:{body.scans}",
        stars=stars,
    )
    if link is None:
        raise HTTPException(502, "Could not create invoice")
    return InvoiceOut(invoice_link=link)


# NOTE: there used to be a POST /api/quota/reset here that zeroed free_scans_used for
# the calling user with no authorization check whatsoever — one curl and the paid tier
# was free forever. It was dead code (no caller in webapp/) and has been removed rather
# than gated. Quota now only resets on the monthly boundary in QuotaService.
