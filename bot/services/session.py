import secrets
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.session import ItemVote, Session, SessionItem, SessionMember, SessionPhoto


class SessionService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create_session(self, admin_tg_id: int) -> Session:
        session = Session(
            admin_tg_id=admin_tg_id,
            invite_code=secrets.token_urlsafe(6)[:8],
        )
        self._db.add(session)
        await self._db.commit()
        await self._db.refresh(session)
        return session

    async def get_session_by_invite(self, invite_code: str) -> Session | None:
        result = await self._db.execute(
            select(Session).where(Session.invite_code == invite_code)
        )
        return result.scalar_one_or_none()

    async def get_session_by_id(self, session_id: UUID | str) -> Session | None:
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        return await self._db.get(Session, session_id)

    async def join_session(
        self, invite_code: str, user_tg_id: int, display_name: str
    ) -> SessionMember | None:
        session = await self.get_session_by_invite(invite_code)
        if session is None:
            return None

        existing = await self._db.execute(
            select(SessionMember).where(
                SessionMember.session_id == session.id,
                SessionMember.user_tg_id == user_tg_id,
            )
        )
        if existing.scalar_one_or_none():
            return None

        member = SessionMember(
            session_id=session.id, user_tg_id=user_tg_id, display_name=display_name
        )
        self._db.add(member)
        await self._db.commit()
        await self._db.refresh(member)
        return member

    async def add_photo(self, session_id: UUID | str, tg_file_id: str) -> SessionPhoto:
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        photo = SessionPhoto(session_id=session_id, tg_file_id=tg_file_id)
        self._db.add(photo)
        await self._db.commit()
        await self._db.refresh(photo)
        return photo

    async def save_ocr_items(
        self, session_id: UUID | str, items_data: list[dict]
    ) -> list[SessionItem]:
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        items = []
        for data in items_data:
            item = SessionItem(
                session_id=session_id,
                name=data["name"],
                price=Decimal(str(data["price"])),
                quantity=data.get("quantity", 1),
            )
            self._db.add(item)
            items.append(item)
        await self._db.commit()
        for item in items:
            await self._db.refresh(item)
        return items

    async def toggle_vote(self, item_id: UUID, user_tg_id: int) -> bool:
        """Returns True if vote added, False if removed."""
        existing = await self._db.execute(
            select(ItemVote).where(
                ItemVote.item_id == item_id, ItemVote.user_tg_id == user_tg_id
            )
        )
        vote = existing.scalar_one_or_none()
        if vote:
            await self._db.delete(vote)
            await self._db.commit()
            return False
        new_vote = ItemVote(item_id=item_id, user_tg_id=user_tg_id)
        self._db.add(new_vote)
        await self._db.commit()
        return True

    async def get_unvoted_items(self, session_id: UUID) -> list[SessionItem]:
        result = await self._db.execute(
            select(SessionItem)
            .where(SessionItem.session_id == session_id)
            .outerjoin(ItemVote)
            .where(ItemVote.id.is_(None))
        )
        return list(result.scalars().all())

    async def get_user_votes(self, session_id: UUID | str, user_tg_id: int) -> set[UUID]:
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        result = await self._db.execute(
            select(ItemVote.item_id)
            .join(SessionItem)
            .where(SessionItem.session_id == session_id, ItemVote.user_tg_id == user_tg_id)
        )
        return set(result.scalars().all())

    async def update_status(self, session_id: UUID | str, status: str) -> None:
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        session = await self._db.get(Session, session_id)
        if session:
            session.status = status
            await self._db.commit()

    async def delete_item(self, item_id: UUID) -> None:
        item = await self._db.get(SessionItem, item_id)
        if item:
            await self._db.delete(item)
            await self._db.commit()

    async def update_item(self, item_id: UUID, name: str, price: Decimal) -> None:
        item = await self._db.get(SessionItem, item_id)
        if item:
            item.name = name
            item.price = price
            await self._db.commit()

    async def delete_unvoted_items(self, session_id: UUID | str) -> None:
        unvoted = await self.get_unvoted_items(session_id)
        for item in unvoted:
            await self._db.delete(item)
        await self._db.commit()
