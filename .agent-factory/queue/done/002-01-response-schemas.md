# Task: Create Pydantic response schemas

## Parent Domain
002-api-schemas

## Description
Создать все Pydantic response-модели в `api/schemas.py`.

Модели должны:
- Иметь `model_config = ConfigDict(from_attributes=True)` для ORM маппинга
- UUID сериализовать как str
- Decimal как float

### Schemas:

```python
class PhotoOut(BaseModel):
    id: str  # UUID as string
    tg_file_id: str
    created_at: datetime

class VoteOut(BaseModel):
    id: str
    item_id: str
    user_tg_id: int
    quantity: int

class ItemOut(BaseModel):
    id: str
    name: str
    price: float  # Decimal → float
    quantity: int
    votes: list[VoteOut]

class MemberOut(BaseModel):
    id: str
    user_tg_id: int
    display_name: str
    tip_percent: int | None
    confirmed: bool
    joined_at: datetime

class SessionOut(BaseModel):
    id: str
    admin_tg_id: int
    invite_code: str
    status: str
    currency: str
    tip_percent: int
    created_at: datetime
    closed_at: datetime | None
    photos: list[PhotoOut]
    items: list[ItemOut]
    members: list[MemberOut]

class SessionBrief(BaseModel):
    id: str
    invite_code: str
    status: str
    created_at: datetime
    member_count: int  # computed field
    item_count: int    # computed field

class OcrItemOut(BaseModel):
    name: str
    price: float
    quantity: int

class OcrResultOut(BaseModel):
    items: list[OcrItemOut]
    total: float
    currency: str
    total_mismatch: bool

class ShareOut(BaseModel):
    user_tg_id: int
    display_name: str
    dishes_total: float
    tip_amount: float
    grand_total: float

class QuotaOut(BaseModel):
    free_scans_left: int
    paid_scans: int
    reset_at: datetime
```

## Files to Create/Modify
- api/schemas.py (create)

## Dependencies
- None (schemas зависят только от pydantic, не от app/auth)

## Tests Required
- `tests/test_api/test_schemas.py`:
  - test_session_out_from_orm — конвертация из ORM-модели
  - test_item_out_from_orm — конвертация с votes
  - test_share_out — корректные поля
  - test_uuid_serialization — UUID → str

## Acceptance Criteria
- [ ] Все response schemas определены
- [ ] from_attributes=True работает для ORM маппинга
- [ ] UUID корректно сериализуется в str
- [ ] Decimal корректно сериализуется в float
- [ ] Тесты проходят
- [ ] Импорт без side effects

## Estimated Complexity
M

## Status: done
## Assigned: worker-92965
