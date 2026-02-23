# Domain: Pydantic API Schemas

## Priority
HIGH

## Scope
- Все Pydantic request/response модели для REST API (`api/schemas.py`)
- Маппинг SQLAlchemy моделей → Pydantic response schemas
- Request validation schemas для мутаций

## Dependencies
- 001-api-foundation (нужен TelegramUser для контекста)

## Key Decisions
- Все response модели наследуют `model_config = ConfigDict(from_attributes=True)` для автоматического маппинга из ORM
- UUID поля сериализуются как строки
- Decimal → float в responses (JSON не поддерживает Decimal)
- Nested schemas: SessionOut содержит items, members, photos

## Acceptance Criteria
- Все response schemas покрывают все поля соответствующих ORM моделей
- Request schemas имеют валидацию (цена > 0, tip_percent 0-100, etc.)
- Schemas можно импортировать без side effects (no DB/settings required)
- Type hints корректны и полны

## Estimated Tasks
- SessionOut, SessionBrief (for listing)
- ItemOut, ItemIn (create/update)
- MemberOut
- VoteIn, VoteOut
- TipIn
- ShareOut (user share breakdown)
- OcrResultOut
- QuotaOut
- PhotoOut
