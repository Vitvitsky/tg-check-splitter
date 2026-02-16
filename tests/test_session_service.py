import pytest

from bot.models.session import Session, SessionItem, SessionMember, SessionPhoto
from bot.services.session import SessionService


@pytest.fixture
def svc(db_session):
    return SessionService(db_session)


async def test_create_session(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    assert session.admin_tg_id == 111
    assert session.status == "created"
    assert len(session.invite_code) == 8


async def test_join_session(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    member = await svc.join_session(session.invite_code, user_tg_id=222, display_name="Bob")
    assert member.user_tg_id == 222
    assert member.session_id == session.id


async def test_join_session_invalid_code(svc):
    result = await svc.join_session("nonexistent", user_tg_id=222, display_name="Bob")
    assert result is None


async def test_join_session_duplicate(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    await svc.join_session(session.invite_code, user_tg_id=222, display_name="Bob")
    dup = await svc.join_session(session.invite_code, user_tg_id=222, display_name="Bob")
    assert dup is None  # already joined


async def test_add_photo(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    photo = await svc.add_photo(session.id, tg_file_id="AgACAgIAA...")
    assert photo.tg_file_id == "AgACAgIAA..."


async def test_save_ocr_items(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    items_data = [
        {"name": "Pizza", "price": 650, "quantity": 1},
        {"name": "Soup", "price": 450, "quantity": 2},
    ]
    items = await svc.save_ocr_items(session.id, items_data)
    assert len(items) == 2


async def test_toggle_vote(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    items = await svc.save_ocr_items(session.id, [{"name": "Pizza", "price": 650, "quantity": 1}])
    item_id = items[0].id

    # Vote on
    voted = await svc.toggle_vote(item_id, user_tg_id=222)
    assert voted is True

    # Vote off
    voted = await svc.toggle_vote(item_id, user_tg_id=222)
    assert voted is False


async def test_get_unvoted_items(svc, db_session):
    session = await svc.create_session(admin_tg_id=111)
    items = await svc.save_ocr_items(session.id, [
        {"name": "Pizza", "price": 650, "quantity": 1},
        {"name": "Soup", "price": 450, "quantity": 1},
    ])
    await svc.toggle_vote(items[0].id, user_tg_id=222)

    unvoted = await svc.get_unvoted_items(session.id)
    assert len(unvoted) == 1
    assert unvoted[0].name == "Soup"
