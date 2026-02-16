from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.config import get_settings
from bot.keyboards.check import ocr_result_kb, photo_collected_kb
from bot.services.ocr import OcrService
from bot.services.quota import QuotaService
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


@router.callback_query(F.data == "ocr_edit")
async def start_edit(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    """Show items list with edit/delete buttons."""
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]

    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)

    buttons = []
    for item in session.items:
        buttons.append([
            InlineKeyboardButton(
                text=f"{item.name} — {item.price}₽",
                callback_data=f"edit_item:{item.id}",
            ),
            InlineKeyboardButton(text="🗑", callback_data=f"del_item:{item.id}"),
        ])
    buttons.append([InlineKeyboardButton(text="➕ Добавить позицию", callback_data="add_item")])
    buttons.append([InlineKeyboardButton(text="✅ Готово", callback_data="ocr_confirm")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text("Редактирование позиций:", reply_markup=kb)


@router.callback_query(F.data.startswith("del_item:"))
async def delete_item(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    from uuid import UUID

    item_id = UUID(callback.data.split(":")[1])
    svc = SessionService(db)
    await svc.delete_item(item_id)
    await callback.answer("Удалено")
    # Refresh the edit view
    await start_edit(callback, state, db)


@router.callback_query(F.data.startswith("edit_item:"))
async def edit_item_prompt(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.split(":")[1]
    await state.update_data(editing_item_id=item_id)
    await state.set_state(CheckStates.editing_item)
    await callback.answer()
    await callback.message.edit_text(
        "Введите новое название и цену через дефис:\nНапример: Пицца Маргарита - 700"
    )


@router.callback_query(F.data == "add_item")
async def add_item_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CheckStates.editing_item)
    await state.update_data(editing_item_id=None)
    await callback.answer()
    await callback.message.edit_text(
        "Введите название и цену через дефис:\nНапример: Тирамису - 380"
    )


@router.message(CheckStates.editing_item)
async def handle_edit_item(message: Message, state: FSMContext, db: AsyncSession):
    from decimal import Decimal, InvalidOperation
    from uuid import UUID

    data = await state.get_data()
    session_id = data["session_id"]

    try:
        name, price_str = message.text.rsplit("-", 1)
        name = name.strip()
        price = Decimal(price_str.strip())
    except (ValueError, InvalidOperation):
        await message.answer("Неверный формат. Пример: Пицца Маргарита - 700")
        return

    svc = SessionService(db)
    editing_item_id = data.get("editing_item_id")

    if editing_item_id is None:
        # Adding new item
        await svc.save_ocr_items(session_id, [{"name": name, "price": price, "quantity": 1}])
        await message.answer(f"✅ Добавлено: {name} — {price}₽")
    else:
        # Editing existing item
        item_id = UUID(editing_item_id)
        await svc.update_item(item_id, name=name, price=price)
        await message.answer(f"✅ Обновлено: {name} — {price}₽")

    await state.set_state(CheckStates.reviewing_ocr)
