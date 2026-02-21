from aiogram import Bot, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from aiogram.utils.i18n import gettext as _
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
    """Receive check photo(s). Only admin (creator) or new users can send photos."""
    svc = SessionService(db)

    data = await state.get_data()
    session_id = data.get("session_id")

    if session_id:
        # If user already has a session, check they are the admin
        session = await svc.get_session_by_id(session_id)
        if session and session.admin_tg_id != message.from_user.id:
            await message.answer(_("You are participant"))
            return
    else:
        session = await svc.create_session(
            admin_tg_id=message.from_user.id,
            admin_display_name=message.from_user.full_name,
        )
        session_id = str(session.id)
        await state.update_data(session_id=session_id)

    file_id = message.photo[-1].file_id  # highest resolution
    await svc.add_photo(session_id, tg_file_id=file_id)

    photo_count = data.get("photo_count", 0) + 1
    await state.update_data(photo_count=photo_count)
    await state.set_state(CheckStates.collecting_photos)

    await message.answer(
        _("Photo accepted").format(n=photo_count),
        reply_markup=photo_collected_kb(_),
    )


@router.callback_query(F.data == "ocr_start")
async def start_ocr(callback: CallbackQuery, state: FSMContext, db: AsyncSession, bot: Bot):
    """Download photos and run OCR."""
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]

    # Quota check (free or paid)
    settings = get_settings()
    quota_svc = QuotaService(db, settings.free_scans_per_month)
    if not await quota_svc.can_scan(callback.from_user.id):
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(
                text=_("Pay stars").format(stars=settings.scan_price_stars),
                callback_data="pay_stars",
            )]
        ])
        await callback.message.edit_text(
            _("Quota exhausted").format(limit=settings.free_scans_per_month),
            reply_markup=kb,
        )
        return
    await quota_svc.use_scan(callback.from_user.id)

    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)

    await callback.message.edit_text(_("Recognizing"))

    # Download photos
    photos_bytes = []
    for photo in session.photos:
        file = await bot.get_file(photo.tg_file_id)
        bio = await bot.download_file(file.file_path)
        photos_bytes.append(bio.read())

    # Run OCR
    settings = get_settings()
    ocr = OcrService(api_key=settings.openrouter_api_key, model=settings.openrouter_model)
    try:
        result = await ocr.parse_receipt(photos_bytes)
    except Exception as e:
        await callback.message.edit_text(
            _("OCR error").format(error=str(e)),
            reply_markup=photo_collected_kb(_),
        )
        return

    # Save items and currency
    await svc.save_ocr_items(
        session_id,
        [{"name": i.name, "price": i.price, "quantity": i.quantity} for i in result.items],
    )
    await svc.update_currency(session_id, result.currency)
    await svc.update_status(session_id, "ocr_done")

    # Format result
    from bot.utils import format_price
    curr = result.currency
    lines = [_("Recognized items") + "\n"]
    for i, item in enumerate(result.items, 1):
        lines.append(f"{i}. {item.name} — {format_price(item.price, curr)} (×{item.quantity})")

    if result.total_mismatch:
        items_sum = sum(i.price for i in result.items)
        lines.append(
            "\n" + _("Items total mismatch").format(
                items_sum=format_price(items_sum, curr),
                total=format_price(result.total, curr),
            )
        )

    lines.append("\n" + _("Receipt total").format(total=format_price(result.total, curr)))

    await callback.message.edit_text(
        "\n".join(lines),
        reply_markup=ocr_result_kb(_),
    )
    await state.set_state(CheckStates.reviewing_ocr)


@router.callback_query(F.data == "ocr_retry")
async def retry_ocr(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    """Reset to photo collection — clear old photos and items."""
    await callback.answer()
    data = await state.get_data()
    session_id = data.get("session_id")

    if session_id:
        svc = SessionService(db)
        await svc.clear_items(session_id)
        await svc.clear_photos(session_id)
        await svc.update_status(session_id, "created")

    await state.update_data(photo_count=0)
    await state.set_state(CheckStates.collecting_photos)
    await callback.message.edit_text(_("Send photo again"))


@router.callback_query(F.data == "ocr_edit")
async def start_edit(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    """Show items list with edit/delete buttons."""
    await callback.answer()
    data = await state.get_data()
    session_id = data["session_id"]

    from bot.utils import format_price
    svc = SessionService(db)
    session = await svc.get_session_by_id(session_id)
    curr = getattr(session, "currency", "RUB") or "RUB"

    buttons = []
    for item in session.items:
        buttons.append([
            InlineKeyboardButton(
                text=f"{item.name} — {format_price(item.price, curr)}",
                callback_data=f"edit_item:{item.id}",
            ),
            InlineKeyboardButton(text="🗑", callback_data=f"del_item:{item.id}"),
        ])
    buttons.append([InlineKeyboardButton(text=_("Add item"), callback_data="add_item")])
    buttons.append([InlineKeyboardButton(text=_("Done"), callback_data="ocr_confirm")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(_("Editing items"), reply_markup=kb)


@router.callback_query(F.data.startswith("del_item:"))
async def delete_item(callback: CallbackQuery, state: FSMContext, db: AsyncSession):
    from uuid import UUID

    item_id = UUID(callback.data.split(":")[1])
    svc = SessionService(db)
    await svc.delete_item(item_id)
    await callback.answer(_("Deleted"))
    # Refresh the edit view
    await start_edit(callback, state, db)


@router.callback_query(F.data.startswith("edit_item:"))
async def edit_item_prompt(callback: CallbackQuery, state: FSMContext):
    item_id = callback.data.split(":")[1]
    await state.update_data(editing_item_id=item_id)
    await state.set_state(CheckStates.editing_item)
    await callback.answer()
    await callback.message.edit_text(_("Edit item prompt"))


@router.callback_query(F.data == "add_item")
async def add_item_prompt(callback: CallbackQuery, state: FSMContext):
    await state.set_state(CheckStates.editing_item)
    await state.update_data(editing_item_id=None)
    await callback.answer()
    await callback.message.edit_text(_("Add item prompt"))


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
        await message.answer(_("Invalid format"))
        return

    svc = SessionService(db)
    editing_item_id = data.get("editing_item_id")

    from bot.utils import format_price
    session = await svc.get_session_by_id(session_id)
    curr = getattr(session, "currency", "RUB") or "RUB"

    if editing_item_id is None:
        await svc.save_ocr_items(session_id, [{"name": name, "price": price, "quantity": 1}])
        await message.answer(_("Item added").format(name=name, price=format_price(price, curr)))
    else:
        item_id = UUID(editing_item_id)
        await svc.update_item(item_id, name=name, price=price)
        await message.answer(_("Item updated").format(name=name, price=format_price(price, curr)))

    await state.set_state(CheckStates.reviewing_ocr)

    session = await svc.get_session_by_id(session_id)
    curr = getattr(session, "currency", "RUB") or "RUB"
    buttons = []
    for item in session.items:
        buttons.append([
            InlineKeyboardButton(
                text=f"{item.name} — {format_price(item.price, curr)}",
                callback_data=f"edit_item:{item.id}",
            ),
            InlineKeyboardButton(text="🗑", callback_data=f"del_item:{item.id}"),
        ])
    buttons.append([InlineKeyboardButton(text=_("Add item"), callback_data="add_item")])
    buttons.append([InlineKeyboardButton(text=_("Done"), callback_data="ocr_confirm")])

    kb = InlineKeyboardMarkup(inline_keyboard=buttons)
    await message.answer(_("Editing items"), reply_markup=kb)
