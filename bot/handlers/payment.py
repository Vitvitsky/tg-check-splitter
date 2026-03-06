import logging

from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from aiogram.utils.i18n import gettext as _
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.keyboards.check import photo_collected_kb
from bot.models.payment import Payment
from bot.services.quota import QuotaService

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "pay_stars")
async def request_payment(callback: CallbackQuery):
    logger.info("user_id=%s payment requested", callback.from_user.id)
    await callback.answer()
    settings = get_settings()
    await callback.message.answer_invoice(
        title=_("Invoice title"),
        description=_("Invoice description"),
        payload="scan_payment",
        currency="XTR",
        prices=[LabeledPrice(label=_("Scan label"), amount=settings.scan_price_stars)],
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(
    message: Message, state: FSMContext, db: AsyncSession, bot: Bot
):
    logger.info("user_id=%s payment success amount=%s", message.from_user.id, message.successful_payment.total_amount)
    settings = get_settings()

    payment = Payment(
        user_tg_id=message.from_user.id,
        session_id=None,
        stars_amount=message.successful_payment.total_amount,
        telegram_charge_id=message.successful_payment.telegram_payment_charge_id,
    )
    db.add(payment)

    # Grant paid scan
    quota_svc = QuotaService(db, settings.free_scans_per_month)
    await quota_svc.grant_paid_scan(message.from_user.id)

    await db.commit()
    await message.answer(
        _("Payment success"),
        reply_markup=photo_collected_kb(_),
    )
