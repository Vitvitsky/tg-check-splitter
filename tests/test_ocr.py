import json
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bot.services.ocr import OcrResult, OcrService


@pytest.fixture
def ocr_service():
    return OcrService(api_key="test-key", model="test/model")


MOCK_LLM_RESPONSE = {
    "choices": [
        {
            "message": {
                "content": json.dumps({
                    "items": [
                        {"name": "Пицца Маргарита", "price": 650, "quantity": 1},
                        {"name": "Том Ям", "price": 450, "quantity": 2},
                    ],
                    "total": 1550,
                    "currency": "RUB",
                })
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
        "choices": [{"message": {"content": json.dumps({
            "items": [{"name": "Пицца Маргарита", "price": 650, "quantity": 1}],
            "total": 650, "currency": "RUB",
        })}}]
    }
    mock_response_1.raise_for_status = MagicMock()

    mock_response_2 = MagicMock()
    mock_response_2.json.return_value = {
        "choices": [{"message": {"content": json.dumps({
            "items": [{"name": "Том Ям", "price": 450, "quantity": 2}],
            "total": 900, "currency": "RUB",
        })}}]
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
        "choices": [{"message": {"content": json.dumps({
            "items": [{"name": "Кола", "price": 200, "quantity": 2}],
            "total": 200, "currency": "RUB",
        })}}]
    }
    resp1.raise_for_status = MagicMock()

    resp2 = MagicMock()
    resp2.json.return_value = {
        "choices": [{"message": {"content": json.dumps({
            "items": [{"name": "Кола", "price": 100, "quantity": 1}],
            "total": 100, "currency": "RUB",
        })}}]
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
                    "content": json.dumps({
                        "items": [{"name": "Item", "price": 100, "quantity": 1}],
                        "total": 200,
                        "currency": "RUB",
                    })
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
