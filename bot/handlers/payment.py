from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.keyboards.check import photo_collected_kb
from bot.models.payment import Payment
from bot.services.quota import QuotaService

router = Router()


@router.callback_query(F.data == "pay_stars")
async def request_payment(callback: CallbackQuery):
    await callback.answer()
    settings = get_settings()
    await callback.message.answer_invoice(
        title="Распознавание чека",
        description="Оплата за OCR-распознавание одного чека",
        payload="scan_payment",
        currency="XTR",
        prices=[LabeledPrice(label="Сканирование чека", amount=settings.scan_price_stars)],
    )


@router.pre_checkout_query()
async def pre_checkout(query: PreCheckoutQuery):
    await query.answer(ok=True)


@router.message(F.successful_payment)
async def successful_payment(
    message: Message, state: FSMContext, db: AsyncSession, bot: Bot
):
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
        "Оплата прошла! Нажмите кнопку, чтобы запустить распознавание.",
        reply_markup=photo_collected_kb(),
    )
