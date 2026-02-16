import pytest
from datetime import datetime, timedelta, timezone

from bot.models.user_quota import UserQuota
from bot.services.quota import QuotaService


@pytest.fixture
def quota_svc(db_session):
    return QuotaService(db_session, free_limit=3)


async def test_new_user_has_quota(quota_svc):
    can_scan = await quota_svc.can_scan_free(user_tg_id=111)
    assert can_scan is True


async def test_use_quota(quota_svc, db_session):
    await quota_svc.use_free_scan(user_tg_id=111)
    quota = await db_session.get(UserQuota, 111)
    assert quota.free_scans_used == 1


async def test_exhaust_quota(quota_svc):
    for _ in range(3):
        await quota_svc.use_free_scan(user_tg_id=111)
    can_scan = await quota_svc.can_scan_free(user_tg_id=111)
    assert can_scan is False


async def test_quota_resets_monthly(quota_svc, db_session):
    quota = UserQuota(
        user_tg_id=111,
        free_scans_used=3,
        quota_reset_at=datetime.now(timezone.utc) - timedelta(days=1),
    )
    db_session.add(quota)
    await db_session.commit()

    can_scan = await quota_svc.can_scan_free(user_tg_id=111)
    assert can_scan is True
