"""Telegram Stars payment settlement.

The invoice itself is created by the API (POST /api/quota/invoice) and opened by the
Mini App via openInvoice() — see api/routes/quota.py. What has to stay in the bot is
the half Telegram will only deliver over the bot connection: the pre-checkout answer
and the successful-payment update that credits the scan.
"""

import logging

from aiogram import F, Router
from aiogram.types import Message, PreCheckoutQuery
from aiogram.utils.i18n import gettext as _
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.models.payment import Payment
from bot.services.quota import QuotaService

logger = logging.getLogger(__name__)
router = Router()

# Payload prefix set by api/routes/quota.py; anything else is not ours.
PAYLOAD_PREFIX = "scans:"


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    if not query.invoice_payload.startswith(PAYLOAD_PREFIX):
        logger.warning("Rejecting unknown invoice payload: %s", query.invoice_payload)
        await query.answer(ok=False, error_message="Unknown invoice")
        return
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(message: Message, db: AsyncSession):
    payment_info = message.successful_payment
    logger.info(
        "user_id=%s payment success amount=%s payload=%s",
        message.from_user.id,
        payment_info.total_amount,
        payment_info.invoice_payload,
    )
    settings = get_settings()

    # Telegram can redeliver a successful_payment update. telegram_payment_charge_id is
    # unique per charge, so an already-recorded id means the scans were already granted
    # and re-granting would hand out free quota on every retry.
    charge_id = payment_info.telegram_payment_charge_id
    existing = await db.execute(select(Payment).where(Payment.telegram_charge_id == charge_id))
    if existing.scalar_one_or_none() is not None:
        logger.info("Duplicate successful_payment for charge %s ignored", charge_id)
        return

    scans = _scans_from_payload(payment_info.invoice_payload)

    db.add(
        Payment(
            user_tg_id=message.from_user.id,
            session_id=None,
            stars_amount=payment_info.total_amount,
            telegram_charge_id=payment_info.telegram_payment_charge_id,
        )
    )

    quota_svc = QuotaService(db, settings.free_scans_per_month)
    for _i in range(scans):
        await quota_svc.grant_paid_scan(message.from_user.id)

    await db.commit()
    await message.answer(_("Payment success"))


def _scans_from_payload(payload: str) -> int:
    """Parse ``scans:<n>`` — falling back to a single scan on anything unexpected."""
    try:
        return max(1, int(payload.removeprefix(PAYLOAD_PREFIX)))
    except ValueError:
        logger.warning("Unparseable invoice payload %r, granting 1 scan", payload)
        return 1
