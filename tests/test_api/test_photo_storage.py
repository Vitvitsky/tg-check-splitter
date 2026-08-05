"""Receipt bytes live on the row, and only until the receipt has been read.

They used to sit in a process-local dict with no eviction: a restart stranded every
in-flight session, the API could not run a second worker, and nothing ever freed them.
"""

from __future__ import annotations

from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from core.models.session import SessionPhoto
from core.services.ocr import OcrItem, OcrResult
from core.services.session import SessionService


@pytest.fixture
async def session_id(db_session):
    svc = SessionService(db_session)
    session = await svc.create_session(admin_tg_id=12345, admin_display_name="Test")
    return str(session.id)


def _good_result() -> OcrResult:
    return OcrResult(
        items=[OcrItem(name="Pizza", price=Decimal("500"), quantity=1)],
        total=Decimal("500"),
        currency="RUB",
    )


async def _stored_bytes(db_session, session_id) -> list[bytes | None]:
    from uuid import UUID

    rows = await db_session.execute(
        select(SessionPhoto.data).where(SessionPhoto.session_id == UUID(session_id))
    )
    return [r[0] for r in rows.all()]


async def test_uploaded_bytes_are_persisted_on_the_row(
    client, auth_headers, session_id, db_session
):
    resp = await client.post(
        f"/api/sessions/{session_id}/photos",
        files={"files": ("r.jpg", b"receipt-bytes", "image/jpeg")},
        headers=auth_headers,
    )
    assert resp.status_code == 201
    assert await _stored_bytes(db_session, session_id) == [b"receipt-bytes"]


async def test_bytes_survive_a_process_restart(client, auth_headers, session_id, db_session):
    """The whole point: state that outlives the worker that accepted the upload."""
    await client.post(
        f"/api/sessions/{session_id}/photos",
        files={"files": ("r.jpg", b"receipt-bytes", "image/jpeg")},
        headers=auth_headers,
    )

    # A fresh service on a fresh identity map stands in for a different process — there
    # is no in-memory handoff left for it to depend on.
    svc = SessionService(db_session)
    db_session.expunge_all()
    assert await svc.get_photo_bytes(session_id) == [b"receipt-bytes"]


async def test_bytes_are_dropped_after_a_successful_ocr(
    client, auth_headers, session_id, db_session
):
    """Where essentially all of the storage goes: the payload dies with its purpose."""
    await client.post(
        f"/api/sessions/{session_id}/photos",
        files={"files": ("r.jpg", b"receipt-bytes", "image/jpeg")},
        headers=auth_headers,
    )

    with patch("api.routes.ocr.OcrService.parse_receipt", AsyncMock(return_value=_good_result())):
        resp = await client.post(f"/api/sessions/{session_id}/ocr", headers=auth_headers)

    assert resp.status_code == 200
    assert await _stored_bytes(db_session, session_id) == [None], "bytes outlived their use"


async def test_bytes_are_kept_when_ocr_fails(client, auth_headers, session_id, db_session):
    """A failed scan is refunded and retryable — throwing the photos away would not be."""
    await client.post(
        f"/api/sessions/{session_id}/photos",
        files={"files": ("r.jpg", b"receipt-bytes", "image/jpeg")},
        headers=auth_headers,
    )

    with patch(
        "api.routes.ocr.OcrService.parse_receipt", AsyncMock(side_effect=ValueError("nope"))
    ):
        resp = await client.post(f"/api/sessions/{session_id}/ocr", headers=auth_headers)

    assert resp.status_code == 422
    assert await _stored_bytes(db_session, session_id) == [b"receipt-bytes"]


async def test_cleared_rows_are_not_offered_to_ocr_again(
    client, auth_headers, session_id, db_session
):
    """After a successful scan the rows remain but carry nothing — OCR must say so."""
    await client.post(
        f"/api/sessions/{session_id}/photos",
        files={"files": ("r.jpg", b"receipt-bytes", "image/jpeg")},
        headers=auth_headers,
    )
    svc = SessionService(db_session)
    await svc.clear_photo_bytes(session_id)

    resp = await client.post(f"/api/sessions/{session_id}/ocr", headers=auth_headers)
    assert resp.status_code == 400


async def test_deleting_a_session_takes_its_photo_bytes_with_it(db_session):
    """The backstop for sessions that never reached OCR — no sweeper needed."""
    svc = SessionService(db_session)
    session = await svc.create_session(admin_tg_id=777, admin_display_name="A")
    await svc.add_photo(session.id, "miniapp-1", data=b"bytes")

    await db_session.delete(session)
    await db_session.commit()

    rows = await db_session.execute(
        select(SessionPhoto).where(SessionPhoto.session_id == session.id)
    )
    assert rows.scalars().all() == []


async def test_session_reads_do_not_carry_the_jpegs(client, auth_headers, session_id):
    """The column is deferred; a session read must not drag megabytes along."""
    await client.post(
        f"/api/sessions/{session_id}/photos",
        files={"files": ("r.jpg", b"receipt-bytes", "image/jpeg")},
        headers=auth_headers,
    )

    resp = await client.get(f"/api/sessions/{session_id}", headers=auth_headers)

    assert resp.status_code == 200
    photo = resp.json()["photos"][0]
    assert "data" not in photo, "photo bytes must never be serialised to clients"
