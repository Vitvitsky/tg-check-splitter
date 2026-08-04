import secrets
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.session import (
    ItemVote,
    Session,
    SessionItem,
    SessionMember,
    SessionPhoto,
    _utcnow,
)


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
        result = await self._db.execute(select(Session).where(Session.invite_code == invite_code))
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
        try:
            await self._db.commit()
        except IntegrityError:
            # Lost the race against a concurrent join (uq_session_members_session_user).
            # Same outcome as the check above: already a member, nothing to do.
            await self._db.rollback()
            return None
        await self._db.refresh(member)
        return member

    async def add_photo(
        self, session_id: UUID | str, tg_file_id: str, data: bytes | None = None
    ) -> SessionPhoto:
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        photo = SessionPhoto(session_id=session_id, tg_file_id=tg_file_id, data=data)
        self._db.add(photo)
        await self._db.commit()
        await self._db.refresh(photo)
        return photo

    async def get_photo_bytes(self, session_id: UUID | str) -> list[bytes]:
        """Receipt bytes for a session, oldest first, skipping already-cleared rows.

        Selects the column explicitly: SessionPhoto.data is deferred so that ordinary
        session reads do not carry the JPEGs, and reading it through the ORM attribute
        would emit one lazy load per photo.
        """
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        result = await self._db.execute(
            select(SessionPhoto.data)
            .where(SessionPhoto.session_id == session_id, SessionPhoto.data.is_not(None))
            .order_by(SessionPhoto.created_at)
        )
        return [row[0] for row in result.all()]

    async def clear_photo_bytes(self, session_id: UUID | str) -> None:
        """Drop the stored bytes once the receipt has been recognised.

        The rows stay — they are the record that photos were uploaded — but the payload
        is what costs storage, and it is dead the moment OCR succeeds.
        """
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        await self._db.execute(
            update(SessionPhoto).where(SessionPhoto.session_id == session_id).values(data=None)
        )
        await self._db.commit()

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

    async def _lock_item(self, item_id: UUID) -> None:
        """Take a row lock on the dish for the rest of this transaction.

        Every claim path reads the total already claimed and then writes. Without a
        lock those two steps interleave: under READ COMMITTED two people tapping the
        last portion at the same moment both read "free" and both insert, so the table
        is billed for two portions of a one-portion dish. The unique constraint does
        not help — it is per (item, user), and these are different users.

        Serialising per dish is cheap: the lock is held for one short transaction and
        only ever contends with other claims on the same dish. Exactly one row is
        locked per call, so these calls cannot deadlock against each other.

        No-op on SQLite (the dialect does not emit FOR UPDATE); the tests that prove
        this works run against PostgreSQL.
        """
        await self._db.execute(
            select(SessionItem.id).where(SessionItem.id == item_id).with_for_update()
        )

    async def cycle_vote(self, item_id: UUID, user_tg_id: int, max_qty: int) -> tuple[int, bool]:
        """Cycle vote: 0 → 1 → 2 → ... until total_claimed exhausted, then 0.
        Returns (new_quantity, overflow_prevented).
        overflow_prevented=True means we blocked increment because item was fully claimed."""
        await self._lock_item(item_id)
        existing = await self._db.execute(
            select(ItemVote).where(ItemVote.item_id == item_id, ItemVote.user_tg_id == user_tg_id)
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
        try:
            await self._db.commit()
        except IntegrityError:
            # A concurrent tap inserted the row first (uq_item_votes_item_user).
            # Report what actually landed instead of failing the request.
            await self._db.rollback()
            return await self._current_vote_quantity(item_id, user_tg_id), False
        return 1, False

    async def _current_vote_quantity(self, item_id: UUID, user_tg_id: int) -> int:
        result = await self._db.execute(
            select(ItemVote.quantity).where(
                ItemVote.item_id == item_id, ItemVote.user_tg_id == user_tg_id
            )
        )
        return result.scalar_one_or_none() or 0

    async def set_vote(
        self, item_id: UUID, user_tg_id: int, quantity: int, max_qty: int
    ) -> tuple[int, bool]:
        """Set vote to exact quantity. Returns (new_quantity, overflow_prevented)."""
        await self._lock_item(item_id)
        existing = await self._db.execute(
            select(ItemVote).where(ItemVote.item_id == item_id, ItemVote.user_tg_id == user_tg_id)
        )
        vote = existing.scalar_one_or_none()

        if quantity <= 0:
            if vote:
                await self._db.delete(vote)
                await self._db.commit()
            return 0, False

        # Total claimed by others
        total_result = await self._db.execute(
            select(ItemVote.quantity).where(
                ItemVote.item_id == item_id, ItemVote.user_tg_id != user_tg_id
            )
        )
        others_claimed = sum(r[0] for r in total_result.all())
        max_for_user = max_qty - others_claimed

        if quantity > max_for_user:
            return (vote.quantity if vote else 0), True

        if vote:
            vote.quantity = quantity
        else:
            vote = ItemVote(item_id=item_id, user_tg_id=user_tg_id, quantity=quantity)
            self._db.add(vote)
        try:
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            return await self._current_vote_quantity(item_id, user_tg_id), False
        return quantity, False

    async def add_vote_all(self, item_id: UUID, user_tg_id: int, qty: int) -> None:
        """Add *qty* units on top of the user's existing claim (for split-equal).

        Adds rather than overwrites: split-equal distributes only the units nobody
        claimed, so a member who already took 2 of 3 must keep those 2.
        """
        if qty <= 0:
            return
        await self._lock_item(item_id)
        await self._stage_vote_units(item_id, user_tg_id, qty)
        try:
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()

    async def _stage_vote_units(self, item_id: UUID, user_tg_id: int, qty: int) -> None:
        """Add *qty* units to the user's claim without committing.

        Split-equal writes for several members at once and must not commit between
        them: each commit would drop the row lock and reopen the window where a
        participant claims a unit the split has already handed to someone else.
        """
        existing = await self._db.execute(
            select(ItemVote).where(ItemVote.item_id == item_id, ItemVote.user_tg_id == user_tg_id)
        )
        vote = existing.scalar_one_or_none()
        if vote:
            vote.quantity += qty
        else:
            self._db.add(ItemVote(item_id=item_id, user_tg_id=user_tg_id, quantity=qty))

    async def split_remaining_equally(self, item: SessionItem, member_ids: list[int]) -> int:
        """Distribute an item's unclaimed units among *member_ids*.

        Returns the number of units handed out, which always equals the number that
        were unclaimed — the previous implementation used ``max(1, remaining // n)``
        and handed out 4 units for 1 unclaimed unit across 3 members, billing the
        table more than the receipt said.

        Units are integers, so ``remaining < len(member_ids)`` cannot be spread over
        everyone; the leftover units go to whoever has claimed the least so far.

        The whole distribution runs under one row lock and one commit, so a
        participant still voting cannot claim a unit that has just been handed out.
        """
        # Lock first, then read: reading the remainder before locking would let a
        # concurrent claim land in between and make the split hand out units that are
        # no longer free.
        await self._lock_item(item.id)
        await self._db.refresh(item, ["votes"])
        claimed_by = {v.user_tg_id: v.quantity for v in item.votes}
        remaining = item.quantity - sum(claimed_by.values())
        if remaining <= 0 or not member_ids:
            return 0

        n = len(member_ids)
        base, extra = divmod(remaining, n)
        # Least-claimed members get the indivisible remainder.
        order = sorted(member_ids, key=lambda uid: (claimed_by.get(uid, 0), uid))

        for position, uid in enumerate(order):
            qty = base + (1 if position < extra else 0)
            if qty:
                await self._stage_vote_units(item.id, uid, qty)
        try:
            await self._db.commit()
        except IntegrityError:
            await self._db.rollback()
            return 0
        return remaining

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

    async def claim_settlement(self, session_id: UUID | str) -> bool:
        """Move a session to ``settled``, once and only once.

        Returns True for the caller that performed the transition and False for every
        later one. The conditional UPDATE is the whole point: two admins tapping
        "settle" together would otherwise both read a non-settled session and both fire
        the push notifications, telling everyone their total twice.

        Settling also closes the session for edits (see ``_require_open`` in the API
        routes), which is what lets the shares be recomputed on demand instead of being
        stored: the inputs can no longer change, so the answer cannot either.
        """
        if isinstance(session_id, str):
            session_id = UUID(session_id)
        result = await self._db.execute(
            update(Session)
            .where(Session.id == session_id, Session.status != "settled")
            .values(status="settled", closed_at=_utcnow())
            .returning(Session.id)
        )
        claimed = result.scalar_one_or_none() is not None
        await self._db.commit()
        return claimed

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

    async def set_member_tip(
        self, session_id: UUID | str, user_tg_id: int, tip_percent: int
    ) -> None:
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
        """Reopen a member's selection without discarding what they already chose.

        This used to also blank ``tip_percent``. Un-confirming means "I am not done
        yet", not "I want no tip", and nothing restored the value afterwards: a member
        who confirmed 20%, changed their mind and confirmed again was settled at 0%.
        Silently — the amount simply came out lower, and the tip they had chosen was
        gone from the database with nothing to compare against.
        """
        member = await self.get_member(session_id, user_tg_id)
        if member:
            member.confirmed = False
            await self._db.commit()
