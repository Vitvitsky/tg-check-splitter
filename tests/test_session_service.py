import pytest

from bot.models.session import Session, SessionItem, SessionMember, SessionPhoto
from bot.services.session import SessionService


@pytest.fixture
def svc(db_session):
    return SessionService(db_session)


async def test_create_session(svc, db_session):
    session = await svc.create_session(admin_tg_id=111, admin_display_name="Admin")
    assert session.admin_tg_id == 111
    assert session.status == "created"
    assert len(session.invite_code) == 8
    assert len(session.members) == 1
    assert session.members[0].user_tg_id == 111
    assert session.members[0].display_name == "Admin"


async def test_join_session(svc, db_session):
    session = await svc.create_session(admin_tg_id=111, admin_display_name="Admin")
    member = await svc.join_session(session.invite_code, user_tg_id=222, display_name="Bob")
    assert member.user_tg_id == 222
    assert member.session_id == session.id


async def test_join_session_invalid_code(svc):
    result = await svc.join_session("nonexistent", user_tg_id=222, display_name="Bob")
    assert result is None


async def test_join_session_duplicate(svc, db_session):
    session = await svc.create_session(admin_tg_id=111, admin_display_name="Admin")
    await svc.join_session(session.invite_code, user_tg_id=222, display_name="Bob")
    dup = await svc.join_session(session.invite_code, user_tg_id=222, display_name="Bob")
    assert dup is None  # already joined


async def test_add_photo(svc, db_session):
    session = await svc.create_session(admin_tg_id=111, admin_display_name="Admin")
    photo = await svc.add_photo(session.id, tg_file_id="AgACAgIAA...")
    assert photo.tg_file_id == "AgACAgIAA..."


async def test_save_ocr_items(svc, db_session):
    session = await svc.create_session(admin_tg_id=111, admin_display_name="Admin")
    items_data = [
        {"name": "Pizza", "price": 650, "quantity": 1},
        {"name": "Soup", "price": 450, "quantity": 2},
    ]
    items = await svc.save_ocr_items(session.id, items_data)
    assert len(items) == 2


async def test_cycle_vote(svc, db_session):
    session = await svc.create_session(admin_tg_id=111, admin_display_name="Admin")
    items = await svc.save_ocr_items(session.id, [{"name": "Pizza", "price": 650, "quantity": 2}])
    item_id = items[0].id

    # 0 → 1
    qty, overflow = await svc.cycle_vote(item_id, user_tg_id=222, max_qty=2)
    assert qty == 1 and not overflow

    # 1 → 2
    qty, overflow = await svc.cycle_vote(item_id, user_tg_id=222, max_qty=2)
    assert qty == 2 and not overflow

    # 2 → 0 (removed)
    qty, overflow = await svc.cycle_vote(item_id, user_tg_id=222, max_qty=2)
    assert qty == 0 and not overflow


async def test_cycle_vote_overflow(svc, db_session):
    """Second user cannot claim when item fully claimed by first user."""
    session = await svc.create_session(admin_tg_id=111, admin_display_name="Admin")
    items = await svc.save_ocr_items(session.id, [{"name": "Coffee", "price": 200, "quantity": 1}])
    item_id = items[0].id

    qty, overflow = await svc.cycle_vote(item_id, user_tg_id=222, max_qty=1)
    assert qty == 1 and not overflow

    qty, overflow = await svc.cycle_vote(item_id, user_tg_id=333, max_qty=1)
    assert qty == 0 and overflow


async def test_get_unvoted_items(svc, db_session):
    session = await svc.create_session(admin_tg_id=111, admin_display_name="Admin")
    items = await svc.save_ocr_items(session.id, [
        {"name": "Pizza", "price": 650, "quantity": 1},
        {"name": "Soup", "price": 450, "quantity": 1},
    ])
    await svc.cycle_vote(items[0].id, user_tg_id=222, max_qty=1)  # unpack not needed

    unvoted = await svc.get_unvoted_items(session.id)
    assert len(unvoted) == 1
    assert unvoted[0].name == "Soup"
