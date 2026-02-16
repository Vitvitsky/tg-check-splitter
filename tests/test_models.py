import uuid
from decimal import Decimal

from bot.models.session import ItemVote, Session, SessionItem, SessionMember, SessionPhoto


async def test_create_session(db_session):
    session = Session(admin_tg_id=123456, invite_code="abc123")
    db_session.add(session)
    await db_session.commit()
    await db_session.refresh(session)
    assert session.id is not None
    assert session.status == "created"
    assert session.tip_percent == 0


async def test_session_with_items_and_votes(db_session):
    session = Session(admin_tg_id=111, invite_code="test1")
    db_session.add(session)
    await db_session.flush()

    item = SessionItem(session_id=session.id, name="Pizza", price=Decimal("650.00"), quantity=1)
    db_session.add(item)
    await db_session.flush()

    vote = ItemVote(item_id=item.id, user_tg_id=222)
    db_session.add(vote)
    await db_session.commit()

    await db_session.refresh(item, attribute_names=["votes"])
    assert len(item.votes) == 1
    assert item.votes[0].user_tg_id == 222


async def test_session_photos(db_session):
    session = Session(admin_tg_id=111, invite_code="test2")
    db_session.add(session)
    await db_session.flush()

    photo = SessionPhoto(session_id=session.id, tg_file_id="AgACAgIAA...")
    db_session.add(photo)
    await db_session.commit()

    await db_session.refresh(session, attribute_names=["photos"])
    assert len(session.photos) == 1


async def test_session_members(db_session):
    session = Session(admin_tg_id=111, invite_code="test3")
    db_session.add(session)
    await db_session.flush()

    member = SessionMember(session_id=session.id, user_tg_id=222, display_name="Alice")
    db_session.add(member)
    await db_session.commit()

    await db_session.refresh(session, attribute_names=["members"])
    assert len(session.members) == 1
    assert session.members[0].display_name == "Alice"
