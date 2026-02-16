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
    mock_response = MagicMock()
    mock_response.json.return_value = MOCK_LLM_RESPONSE
    mock_response.raise_for_status = MagicMock()

    with patch(
        "httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response
    ) as mock_post:
        result = await ocr_service.parse_receipt([b"photo1", b"photo2"])

    # Verify multiple images sent in one request
    call_args = mock_post.call_args
    messages = call_args[1]["json"]["messages"]
    # User message is the second message (after system)
    user_content = messages[1]["content"]
    image_parts = [p for p in user_content if p.get("type") == "image_url"]
    assert len(image_parts) == 2


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
