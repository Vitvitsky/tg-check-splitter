"""OCR billing: a scan is charged for a parsed receipt, not for an attempt.

The scan used to be consumed before the LLM was contacted and never given back, so a
provider timeout, a rate limit, an unreadable photo — or even a session whose photo
bytes had been lost — cost the user a scan and produced nothing.
"""

from __future__ import annotations

import asyncio
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from bot.services.ocr import OcrItem, OcrResult
from bot.services.quota import QuotaService
from bot.services.session import SessionService


@pytest.fixture
async def session_id(db_session):
    svc = SessionService(db_session)
    session = await svc.create_session(admin_tg_id=12345, admin_display_name="Test")
    return str(session.id)


@pytest.fixture
async def session_with_photo(client, auth_headers, session_id):
    """A session carrying one uploaded photo, ready for OCR."""
    await client.post(
        f"/api/sessions/{session_id}/photos",
        files={"files": ("receipt.jpg", b"fake-jpeg-bytes", "image/jpeg")},
        headers=auth_headers,
    )
    return session_id


def _good_result() -> OcrResult:
    return OcrResult(
        items=[OcrItem(name="Pizza", price=Decimal("500"), quantity=1)],
        total=Decimal("500"),
        currency="RUB",
    )


async def _free_left(db_session, user_id=12345) -> int:
    free_left, _paid, _reset = await QuotaService(db_session, 3).get_quota_info(user_id)
    return free_left


# ---------------------------------------------------------------------------
# Refunds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("failure", "expected_status"),
    [
        (ValueError("LLM returned invalid JSON"), 422),
        (httpx.ConnectError("provider down"), 502),
        (asyncio.TimeoutError(), 504),
    ],
)
async def test_failed_ocr_refunds_the_scan(
    client, auth_headers, session_with_photo, db_session, failure, expected_status
):
    before = await _free_left(db_session)

    with patch("api.routes.ocr.OcrService.parse_receipt", AsyncMock(side_effect=failure)):
        resp = await client.post(f"/api/sessions/{session_with_photo}/ocr", headers=auth_headers)

    assert resp.status_code == expected_status
    assert await _free_left(db_session) == before, "a failed scan must not be billed"


async def test_the_deadline_itself_fires_and_refunds(
    client, auth_headers, session_with_photo, db_session
):
    """Not just "a TimeoutError maps to 504" — the asyncio.timeout guard must trip.

    The guard exists so the request fails *before* nginx's proxy_read_timeout kills it;
    once nginx has cut the connection there is no handler left to issue the refund.
    """
    before = await _free_left(db_session)

    async def never_finishes(*_args, **_kwargs):
        await asyncio.sleep(30)

    with (
        patch("api.routes.ocr._OCR_DEADLINE_SECONDS", 0.05),
        patch("api.routes.ocr.OcrService.parse_receipt", never_finishes),
    ):
        resp = await client.post(f"/api/sessions/{session_with_photo}/ocr", headers=auth_headers)

    assert resp.status_code == 504
    assert await _free_left(db_session) == before


async def test_receipt_with_no_items_is_refunded(
    client, auth_headers, session_with_photo, db_session
):
    """A parse that succeeds but finds nothing gave the user nothing to pay for."""
    empty = OcrResult(items=[], total=Decimal("0"), currency="RUB")
    before = await _free_left(db_session)

    with patch("api.routes.ocr.OcrService.parse_receipt", AsyncMock(return_value=empty)):
        resp = await client.post(f"/api/sessions/{session_with_photo}/ocr", headers=auth_headers)

    assert resp.status_code == 422
    assert await _free_left(db_session) == before


async def test_successful_ocr_is_billed(client, auth_headers, session_with_photo, db_session):
    before = await _free_left(db_session)

    with patch("api.routes.ocr.OcrService.parse_receipt", AsyncMock(return_value=_good_result())):
        resp = await client.post(f"/api/sessions/{session_with_photo}/ocr", headers=auth_headers)

    assert resp.status_code == 200
    assert await _free_left(db_session) == before - 1


async def test_missing_photo_bytes_are_not_billed(client, auth_headers, session_id, db_session):
    """Photo bytes live in process memory; a restart loses them. That is not billable."""
    before = await _free_left(db_session)

    resp = await client.post(f"/api/sessions/{session_id}/ocr", headers=auth_headers)

    assert resp.status_code == 400
    assert await _free_left(db_session) == before


# ---------------------------------------------------------------------------
# Refunds land in the bucket they were charged from
# ---------------------------------------------------------------------------


async def test_paid_scan_is_refunded_as_paid_not_free(
    client, auth_headers, session_with_photo, db_session
):
    """With the free allowance gone the charge is paid — the refund must be too."""
    quota = QuotaService(db_session, 3)
    for _ in range(3):
        await quota.use_free_scan(12345)
    await quota.grant_paid_scan(12345)

    with patch(
        "api.routes.ocr.OcrService.parse_receipt", AsyncMock(side_effect=ValueError("nope"))
    ):
        resp = await client.post(f"/api/sessions/{session_with_photo}/ocr", headers=auth_headers)

    assert resp.status_code == 422
    free_left, paid, _reset = await quota.get_quota_info(12345)
    assert paid == 1, "the paid scan must come back as paid"
    assert free_left == 0, "and must not be converted into free allowance"


async def test_exhausted_quota_is_rejected_before_any_ocr(
    client, auth_headers, session_with_photo, db_session
):
    quota = QuotaService(db_session, 3)
    for _ in range(3):
        await quota.use_free_scan(12345)

    parse = AsyncMock(return_value=_good_result())
    with patch("api.routes.ocr.OcrService.parse_receipt", parse):
        resp = await client.post(f"/api/sessions/{session_with_photo}/ocr", headers=auth_headers)

    assert resp.status_code == 402
    parse.assert_not_awaited()


# ---------------------------------------------------------------------------
# Photo count cap
# ---------------------------------------------------------------------------


async def test_upload_rejects_more_photos_than_a_receipt_may_have(
    client, auth_headers, session_id
):
    """The cap is on the session total, not the batch — uploads are incremental."""
    from api.routes.ocr import _MAX_PHOTOS

    for _ in range(_MAX_PHOTOS):
        resp = await client.post(
            f"/api/sessions/{session_id}/photos",
            files={"files": ("r.jpg", b"bytes", "image/jpeg")},
            headers=auth_headers,
        )
        assert resp.status_code == 201

    resp = await client.post(
        f"/api/sessions/{session_id}/photos",
        files={"files": ("one-too-many.jpg", b"bytes", "image/jpeg")},
        headers=auth_headers,
    )
    assert resp.status_code == 400
    assert str(_MAX_PHOTOS) in resp.json()["detail"]
