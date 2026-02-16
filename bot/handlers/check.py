from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.keyboards.check import ocr_result_kb, photo_collected_kb
from bot.services.ocr import OcrService
from bot.services.session import SessionService

router = Router()


class CheckStates(StatesGroup):
    collecting_photos = State()
    reviewing_ocr = State()
    editing_item = State()


@router.message(F.photo)
async def handle_photo(message: Message, state: FSMContext, db: AsyncSession):
    """Receive check photo(s)."""
    svc = SessionService(db)

    data = await state.get_data()
    session_id = data.get("session_id")

    if not session_id:
        session = await svc.create_session(admin_tg_id=message.from_user.id)
        session_id = str(session.id)
        await state.update_data(session_id=session_id)

    file_id = message.photo[-1].file_id  # highest resolution
    await svc.add_photo(session_id, tg_file_id=file_id)

    photo_count = data.get("photo_count", 0) + 1
    await state.update_data(photo_count=photo_count)
    await state.set_state(CheckStates.collecting_photos)

    await message.answer(
        f"Фото {photo_count} принято. Отправьте ещё или нажмите:",
        reply_markup=photo_collected_kb(),
    )


@router.callback_query(F.data == "ocr_start")
async def start_ocr(callback: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot):
    """Download photos and run OCR."""
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)

    await callback.message.edit_text("⏳ Распознаю чек...")

    # Download photos
    photos_bytes = []
    for photo in session.photos:
        file = await bot.get_file(photo.tg_file_id)
        bio = await bot.download_file(file.file_path)
        photos_bytes.append(bio.read())

    # Run OCR
    settings = get_settings()
    ocr = OcrService(api_key=settings.openrouter_api_key, model=settings.openrouter_model)
    result = await ocr.parse_receipt(photos_bytes)

    # Save items
    await svc.save_ocr_items(
        session_id,
        [{"name": i.name, "price": i.price, "quantity": i.quantity} for i in result.items],
    )

    await svc.update_status(session_id, "voting")

    # Format result
    lines = ["📋 Распознанные позиции:\n"]
    for i, item in enumerate(result.items, 1):
        lines.append(f"{i}. {item.name} — {item.price}₽ (×{item.quantity})")

    if result.total_mismatch:
        items_sum = sum(i.price for i in result.items)
        lines.append(
            f"\n⚠️ Сумма позиций ({items_sum}₽) не совпадает с итогом чека ({result.total}₽)"
        )

    lines.append(f"\nИтого по чеку: {result.total}₽")

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=ocr_result_kb(),
    )
    await state.set_state(CheckStates.reviewing_ocr)


@router.callback_query(F.data == "ocr_retry")
async def retry_ocr(callback: CallbackQuery, state: FSMContext):
    """Reset to photo collection."""
    await callback.answer()
    await state.update_data(photo_count=0)
    await state.set_state(CheckStates.collecting_photos)
    await callback.message.edit_text("Отправьте фото чека заново.")
