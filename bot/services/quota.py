from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from bot.models.user_quota import UserQuota


def _next_month_start() -> datetime:
    now = datetime.now(timezone.utc)
    if now.month == 12:
        return now.replace(year=now.year + 1, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    return now.replace(month=now.month + 1, day=1, hour=0, minute=0, second=0, microsecond=0)


class QuotaService:
    def __init__(self, db: AsyncSession, free_limit: int):
        self._db = db
        self._free_limit = free_limit

    async def _get_or_create(self, user_tg_id: int) -> UserQuota:
        quota = await self._db.get(UserQuota, user_tg_id)
        if quota is None:
            quota = UserQuota(
                user_tg_id=user_tg_id,
                free_scans_used=0,
                quota_reset_at=_next_month_start(),
            )
            self._db.add(quota)
            await self._db.commit()
            await self._db.refresh(quota)
        return quota

    async def can_scan_free(self, user_tg_id: int) -> bool:
        quota = await self._get_or_create(user_tg_id)
        now = datetime.now(timezone.utc)
        reset_at = quota.quota_reset_at
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)
        if now >= reset_at:
            quota.free_scans_used = 0
            quota.quota_reset_at = _next_month_start()
            await self._db.commit()
        return quota.free_scans_used < self._free_limit

    async def use_free_scan(self, user_tg_id: int) -> None:
        quota = await self._get_or_create(user_tg_id)
        quota.free_scans_used += 1
        await self._db.commit()

    async def grant_paid_scan(self, user_tg_id: int) -> None:
        quota = await self._get_or_create(user_tg_id)
        quota.paid_scans += 1
        await self._db.commit()

    async def use_paid_scan(self, user_tg_id: int) -> bool:
        """Try to use a paid scan. Returns True if successful."""
        quota = await self._get_or_create(user_tg_id)
        if quota.paid_scans > 0:
            quota.paid_scans -= 1
            await self._db.commit()
            return True
        return False

    async def can_scan(self, user_tg_id: int) -> bool:
        """Check if user can scan (free or paid)."""
        if await self.can_scan_free(user_tg_id):
            return True
        quota = await self._get_or_create(user_tg_id)
        return quota.paid_scans > 0

    async def use_scan(self, user_tg_id: int) -> bool:
        """Use a scan — free first, then paid. Returns True if successful."""
        if await self.can_scan_free(user_tg_id):
            await self.use_free_scan(user_tg_id)
            return True
        return await self.use_paid_scan(user_tg_id)

    async def get_quota_info(self, user_tg_id: int) -> tuple[int, int, datetime]:
        """Return (free_left, paid_scans, reset_at)."""
        quota = await self._get_or_create(user_tg_id)
        now = datetime.now(timezone.utc)
        reset_at = quota.quota_reset_at
        if reset_at.tzinfo is None:
            reset_at = reset_at.replace(tzinfo=timezone.utc)
        if now >= reset_at:
            quota.free_scans_used = 0
            quota.quota_reset_at = _next_month_start()
            await self._db.commit()
            await self._db.refresh(quota)
            reset_at = quota.quota_reset_at
        free_left = max(0, self._free_limit - quota.free_scans_used)
        return free_left, quota.paid_scans, reset_at
