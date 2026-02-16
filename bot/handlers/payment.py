from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.models.payment import Payment

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
async def successful_payment(message: Message, db: AsyncSession):
    payment = Payment(
        user_tg_id=message.from_user.id,
        session_id=None,
        stars_amount=message.successful_payment.total_amount,
        telegram_charge_id=message.successful_payment.telegram_payment_charge_id,
    )
    db.add(payment)
    await db.commit()
    await message.answer("Оплата прошла! Теперь отправьте фото чека.")
