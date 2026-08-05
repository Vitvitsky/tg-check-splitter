import asyncio
import json
import time
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.services.ocr import OcrItem, OcrResult, OcrService


@pytest.fixture
def ocr_service():
    return OcrService(api_key="test-key", model="test/model")


MOCK_LLM_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": json.dumps(
                    {
                        "items": [
                            {"name": "Пицца Маргарита", "price": 650, "quantity": 1},
                            {"name": "Том Ям", "price": 450, "quantity": 2},
                        ],
                        "total": 1550,
                        "currency": "RUB",
                    }
                )
            }
        }
    ]
}


async def test_parse_receipt_single_photo(ocr_service):
    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_LLM_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await ocr_service.parse_receipt([b"fake-image-bytes"])

    assert isinstance(result, OcrResult)
    assert len(result.items) == 2
    assert result.items[0].name == "Пицца Маргарита"
    assert result.items[0].price == Decimal("650")
    assert result.total == Decimal("1550")


async def test_parse_receipt_multiple_photos(ocr_service):
    """Multiple photos are processed one by one and results merged."""
    mock_response_1 = MagicMock()
    mock_response_1.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "items": [{"name": "Пицца Маргарита", "price": 650, "quantity": 1}],
                            "total": 650,
                            "currency": "RUB",
                        }
                    )
                }
            }
        ]
    }
    mock_response_1.raise_for_status = MagicMock()

    mock_response_2 = MagicMock()
    mock_response_2.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "items": [{"name": "Том Ям", "price": 450, "quantity": 2}],
                            "total": 900,
                            "currency": "RUB",
                        }
                    )
                }
            }
        ]
    }
    mock_response_2.raise_for_status = MagicMock()

    with patch(
        "httpx.AsyncClient.post",
        new_callable=AsyncMock,
        side_effect=[mock_response_1, mock_response_2],
    ) as mock_post:
        result = await ocr_service.parse_receipt([b"photo1", b"photo2"])

    # Each photo gets its own LLM call
    assert mock_post.call_count == 2
    # Results are merged
    assert len(result.items) == 2
    assert result.total == Decimal("1550")
    assert result.items[0].name == "Пицца Маргарита"
    assert result.items[1].name == "Том Ям"


async def test_parse_receipt_deduplicates_items(ocr_service):
    """Duplicate items across photos are merged by name."""
    resp1 = MagicMock()
    resp1.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "items": [{"name": "Кола", "price": 200, "quantity": 2}],
                            "total": 200,
                            "currency": "RUB",
                        }
                    )
                }
            }
        ]
    }
    resp1.raise_for_status = MagicMock()

    resp2 = MagicMock()
    resp2.json.return_value = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "items": [{"name": "Кола", "price": 100, "quantity": 1}],
                            "total": 100,
                            "currency": "RUB",
                        }
                    )
                }
            }
        ]
    }
    resp2.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, side_effect=[resp1, resp2]):
        result = await ocr_service.parse_receipt([b"p1", b"p2"])

    # Same item merged into one
    assert len(result.items) == 1
    assert result.items[0].name == "Кола"
    assert result.items[0].quantity == 3
    assert result.items[0].price == Decimal("300")
    assert result.total == Decimal("300")


async def test_validation_warning_on_mismatch(ocr_service):
    bad_response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            "items": [{"name": "Item", "price": 100, "quantity": 1}],
                            "total": 200,
                            "currency": "RUB",
                        }
                    )
                }
            }
        ]
    }
    mock_response = MagicMock()
    mock_response.json.return_value = bad_response
    mock_response.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
        result = await ocr_service.parse_receipt([b"photo"])

    assert result.total_mismatch is True


# ---------------------------------------------------------------------------
# Multi-photo receipts are parsed concurrently
# ---------------------------------------------------------------------------


async def test_photos_are_parsed_concurrently_not_one_after_another():
    """Sequential parsing is what pushed multi-photo receipts past nginx's timeout.

    Four photos at 120 s each is 480 s sequentially — nginx cuts the connection at
    300 s and the user gets a 504 for a scan they were already charged for. Run
    together, the wall clock is one photo's worth.
    """
    delay = 0.2
    photo_count = 4

    async def slow_parse(_self, _photo):
        await asyncio.sleep(delay)
        return OcrResult(
            items=[OcrItem(name="Item", price=Decimal("100"), quantity=1)],
            total=Decimal("100"),
            currency="RUB",
        )

    svc = OcrService("key", "model")
    with patch.object(OcrService, "_parse_single_photo", slow_parse):
        started = time.perf_counter()
        result = await svc.parse_receipt([b"a", b"b", b"c", b"d"])
        elapsed = time.perf_counter() - started

    assert len(result.items) == 1  # same name -> merged
    assert result.items[0].quantity == photo_count
    assert elapsed < delay * photo_count / 2, (
        f"took {elapsed:.2f}s for {photo_count} photos of {delay}s — looks sequential"
    )


async def test_progress_is_reported_for_every_photo():
    """The Mini App renders this over WebSocket; it must reach `total`."""

    async def fast_parse(_self, _photo):
        return OcrResult(items=[], total=Decimal("0"), currency="RUB")

    seen: list[tuple[int, int]] = []

    async def on_progress(completed: int, total: int) -> None:
        seen.append((completed, total))

    svc = OcrService("key", "model")
    with patch.object(OcrService, "_parse_single_photo", fast_parse):
        await svc.parse_receipt([b"a", b"b", b"c"], on_progress=on_progress)

    assert len(seen) == 3
    assert {total for _done, total in seen} == {3}
    assert sorted(done for done, _total in seen) == [1, 2, 3]


async def test_progress_is_reported_for_a_single_photo():
    """The single-photo path short-circuits the gather — it must still report."""

    async def fast_parse(_self, _photo):
        return OcrResult(items=[], total=Decimal("0"), currency="RUB")

    seen: list[tuple[int, int]] = []

    svc = OcrService("key", "model")
    with patch.object(OcrService, "_parse_single_photo", fast_parse):
        await svc.parse_receipt([b"only"], on_progress=lambda c, t: _record(seen, c, t))

    assert seen == [(1, 1)]


async def _record(sink: list, completed: int, total: int) -> None:
    sink.append((completed, total))
