import base64
import json
from dataclasses import dataclass
from decimal import Decimal

import httpx

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """\
You are a receipt parser. Extract all line items from the receipt photo(s).
If multiple photos are provided, they are parts of the same receipt — merge items and remove duplicates.

Return ONLY valid JSON (no markdown, no explanation):
{
  "items": [{"name": "Item name", "price": 123.45, "quantity": 1}],
  "total": 1234.56,
  "currency": "RUB"
}

Rules:
- price is the total price for that line (price × quantity already multiplied)
- quantity is how many of that item
- total is the receipt grand total
- If you can't read a value, make your best guess and note it in the name with (?)
"""


@dataclass
class OcrItem:
    name: str
    price: Decimal
    quantity: int


@dataclass
class OcrResult:
    items: list[OcrItem]
    total: Decimal
    currency: str
    total_mismatch: bool = False


class OcrService:
    def __init__(self, api_key: str, model: str):
        self._api_key = api_key
        self._model = model

    async def parse_receipt(self, photos: list[bytes]) -> OcrResult:
        content: list[dict] = [{"type": "text", "text": "Parse this receipt:"}]
        for photo in photos:
            b64 = base64.b64encode(photo).decode()
            content.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{b64}"},
            })

        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": content},
                    ],
                },
            )
            response.raise_for_status()

        raw = response.json()["choices"][0]["message"]["content"]
        raw = raw.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        data = json.loads(raw)

        items = [
            OcrItem(
                name=i["name"],
                price=Decimal(str(i["price"])),
                quantity=i.get("quantity", 1),
            )
            for i in data["items"]
        ]

        total = Decimal(str(data["total"]))
        items_sum = sum(i.price for i in items)
        mismatch = abs(items_sum - total) > total * Decimal("0.05") if total else False

        return OcrResult(
            items=items,
            total=total,
            currency=data.get("currency", "RUB"),
            total_mismatch=mismatch,
        )
