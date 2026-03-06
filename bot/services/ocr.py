import base64
import json
import logging
import re
from dataclasses import dataclass
from decimal import Decimal

import httpx

logger = logging.getLogger(__name__)

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = """\
You are a receipt parser. Extract all line items from the receipt photo.

Return ONLY valid JSON (no markdown, no explanation):
{
  "items": [{"name": "Item name", "price": 123.45, "quantity": 1}],
  "total": 1234.56,
  "currency": "RUB"
}

Currency codes: RUB, EUR, USD, GBP, UAH, etc. Use the code from the receipt.

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
        """Parse receipt photos one by one, then merge results."""
        if len(photos) == 1:
            return await self._parse_single_photo(photos[0])

        results: list[OcrResult] = []
        for i, photo in enumerate(photos):
            logger.info("OCR: processing photo %d/%d", i + 1, len(photos))
            result = await self._parse_single_photo(photo)
            results.append(result)

        return self._merge_results(results)

    async def _parse_single_photo(self, photo: bytes) -> OcrResult:
        """Send a single photo to the LLM and parse the response."""
        b64 = base64.b64encode(photo).decode()
        content: list[dict] = [
            {"type": "text", "text": "Parse this receipt:"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]

        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                OPENROUTER_URL,
                headers={"Authorization": f"Bearer {self._api_key}"},
                json={
                    "model": self._model,
                    "max_tokens": 2048,
                    "messages": [
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": content},
                    ],
                },
            )
            response.raise_for_status()

        body = response.json()
        raw = body["choices"][0]["message"]["content"]
        logger.info("OCR raw response: %s", raw[:500] if raw else "<empty>")

        return self._parse_llm_response(raw, body)

    @staticmethod
    def _parse_llm_response(raw: str | None, body: dict) -> OcrResult:
        """Extract structured OcrResult from raw LLM text."""
        if not raw or not raw.strip():
            raise ValueError(f"LLM returned empty content. Full response: {json.dumps(body)[:300]}")

        raw = raw.strip()
        # Strip special tokens from some models (e.g. glm: <|begin_of_box|>...<|end_of_box|>)
        raw = re.sub(r"<\|[a-z_]+\|>", "", raw).strip()
        # Strip markdown code fences
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        # Extract JSON object even if surrounded by text
        match = re.search(r"\{[\s\S]*\}", raw)
        if match:
            raw = match.group(0)

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            raise ValueError(f"LLM returned invalid JSON: {raw[:300]}")

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

    @staticmethod
    def _merge_results(results: list["OcrResult"]) -> "OcrResult":
        """Merge multiple per-photo OCR results, deduplicating items by name."""
        merged_items: dict[str, OcrItem] = {}
        total = Decimal(0)
        currency = results[0].currency if results else "RUB"
        any_mismatch = False

        for result in results:
            total += result.total
            any_mismatch = any_mismatch or result.total_mismatch
            for item in result.items:
                key = item.name.strip().lower()
                if key in merged_items:
                    existing = merged_items[key]
                    merged_items[key] = OcrItem(
                        name=existing.name,
                        price=existing.price + item.price,
                        quantity=existing.quantity + item.quantity,
                    )
                else:
                    merged_items[key] = OcrItem(
                        name=item.name,
                        price=item.price,
                        quantity=item.quantity,
                    )

        all_items = list(merged_items.values())
        items_sum = sum(i.price for i in all_items)
        mismatch = abs(items_sum - total) > total * Decimal("0.05") if total else False

        return OcrResult(
            items=all_items,
            total=total,
            currency=currency,
            total_mismatch=mismatch or any_mismatch,
        )
