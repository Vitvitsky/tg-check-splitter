import secrets
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.session import ItemVote, Session, SessionItem, SessionMember, SessionPhoto


class SessionService:
    def __init__(self, db: AsyncSession):
        self._db = db

    async def create_session(self, admin_tg_id: int, admin_display_name: str) -> Session:
        session = Session(
            admin_tg_id=admin_tg_id,
            invite_code=secrets.token_urlsafe(6)[:8],
        )
        self._db.add(session)
        await self._db.flush()

        member = SessionMember(
            session_id=session.id,
            user_tg_id=admin_tg_id,
            display_name=admin_display_name,
        )
        self._db.add(member)
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

    async def update_currency(self, session_id: UUID | str, currency: str) -> None:
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        session = await self._db.get(Session, session_id)
        if session:
            session.currency = currency[:8] if currency else "RUB"
            await self._db.commit()

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

    async def cycle_vote(
        self, item_id: UUID, user_tg_id: int, max_qty: int
    ) -> tuple[int, bool]:
        """Cycle vote: 0 → 1 → 2 → ... until total_claimed exhausted, then 0.
        Returns (new_quantity, overflow_prevented).
        overflow_prevented=True means we blocked increment because item was fully claimed."""
        existing = await self._db.execute(
            select(ItemVote).where(
                ItemVote.item_id == item_id, ItemVote.user_tg_id == user_tg_id
            )
        )
        vote = existing.scalar_one_or_none()

        # Total claimed by all users
        total_result = await self._db.execute(
            select(ItemVote.quantity).where(ItemVote.item_id == item_id)
        )
        total_claimed = sum(r[0] for r in total_result.all())

        if vote:
            if vote.quantity >= max_qty:
                await self._db.delete(vote)
                await self._db.commit()
                return 0, False
            if total_claimed >= max_qty:
                return vote.quantity, True
            vote.quantity += 1
            await self._db.commit()
            return vote.quantity, False
        if total_claimed >= max_qty:
            return 0, True
        new_vote = ItemVote(item_id=item_id, user_tg_id=user_tg_id, quantity=1)
        self._db.add(new_vote)
        await self._db.commit()
        return 1, False

    async def add_vote_all(self, item_id: UUID, user_tg_id: int, qty: int) -> None:
        """Add a vote with specific quantity (for split-equal)."""
        existing = await self._db.execute(
            select(ItemVote).where(
                ItemVote.item_id == item_id, ItemVote.user_tg_id == user_tg_id
            )
        )
        vote = existing.scalar_one_or_none()
        if vote:
            vote.quantity = qty
        else:
            self._db.add(ItemVote(item_id=item_id, user_tg_id=user_tg_id, quantity=qty))
        await self._db.commit()

    async def get_unvoted_items(self, session_id: UUID | str) -> list[SessionItem]:
        """Items where total claimed < item quantity."""
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        # Fresh query to avoid stale relationship cache
        result = await self._db.execute(
            select(SessionItem).where(SessionItem.session_id == session_id)
        )
        items = list(result.scalars().all())
        unvoted = []
        for item in items:
            # Refresh votes relationship
            await self._db.refresh(item, ["votes"])
            total_claimed = sum(v.quantity for v in item.votes)
            if total_claimed < item.quantity:
                unvoted.append(item)
        return unvoted

    async def get_user_votes(self, session_id: UUID | str, user_tg_id: int) -> dict[UUID, int]:
        """Returns {item_id: claimed_quantity}."""
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        result = await self._db.execute(
            select(ItemVote.item_id, ItemVote.quantity)
            .join(SessionItem)
            .where(SessionItem.session_id == session_id, ItemVote.user_tg_id == user_tg_id)
        )
        return {row.item_id: row.quantity for row in result.all()}

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

    async def clear_photos(self, session_id: UUID | str) -> None:
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        result = await self._db.execute(
            select(SessionPhoto).where(SessionPhoto.session_id == session_id)
        )
        for photo in result.scalars().all():
            await self._db.delete(photo)
        await self._db.commit()

    async def clear_items(self, session_id: UUID | str) -> None:
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        result = await self._db.execute(
            select(SessionItem).where(SessionItem.session_id == session_id)
        )
        for item in result.scalars().all():
            await self._db.delete(item)
        await self._db.commit()

    async def get_members(self, session_id: UUID | str) -> list[SessionMember]:
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        result = await self._db.execute(
            select(SessionMember).where(SessionMember.session_id == session_id)
        )
        return list(result.scalars().all())

    async def get_member(self, session_id: UUID | str, user_tg_id: int) -> SessionMember | None:
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        result = await self._db.execute(
            select(SessionMember).where(
                SessionMember.session_id == session_id,
                SessionMember.user_tg_id == user_tg_id,
            )
        )
        return result.scalar_one_or_none()

    async def set_member_tip(self, session_id: UUID | str, user_tg_id: int, tip_percent: int) -> None:
        member = await self.get_member(session_id, user_tg_id)
        if member:
            member.tip_percent = tip_percent
            await self._db.commit()

    async def confirm_member(self, session_id: UUID | str, user_tg_id: int) -> None:
        member = await self.get_member(session_id, user_tg_id)
        if member:
            member.confirmed = True
            await self._db.commit()

    async def unconfirm_member(self, session_id: UUID | str, user_tg_id: int) -> None:
        member = await self.get_member(session_id, user_tg_id)
        if member:
            member.confirmed = False
            member.tip_percent = None
            await self._db.commit()
