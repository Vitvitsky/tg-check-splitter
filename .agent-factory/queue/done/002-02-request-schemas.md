# Task: Create Pydantic request schemas

## Parent Domain
002-api-schemas

## Description
Добавить в `api/schemas.py` все request-модели с валидацией.

### Schemas:

```python
class VoteIn(BaseModel):
    item_id: str  # UUID as string

class TipIn(BaseModel):
    tip_percent: int = Field(ge=0, le=100)

class ItemIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)
    quantity: int = Field(ge=1, default=1)

class ItemUpdateIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)

class ItemsUpdateIn(BaseModel):
    items: list[ItemIn]

class SessionCreateIn(BaseModel):
    # Ничего не нужно — admin_tg_id берётся из auth
    pass
    # Опционально: currency
    currency: str = Field(default="RUB", max_length=8)
```

## Files to Create/Modify
- api/schemas.py (modify) — добавить request schemas

## Dependencies
- 002-01-response-schemas (файл уже создан)

## Tests Required
- `tests/test_api/test_schemas.py` (дополнить):
  - test_tip_in_validation — tip_percent 0-100, отклоняет -1 и 101
  - test_item_in_validation — price > 0, name non-empty
  - test_vote_in — item_id обязателен

## Acceptance Criteria
- [ ] Все request schemas с валидацией
- [ ] Валидация отклоняет невалидные данные (negative price, tip > 100, etc.)
- [ ] Тесты проходят

## Estimated Complexity
S

## Status: done
## Assigned: worker-2867
