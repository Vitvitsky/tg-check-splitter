"""Pydantic schemas for API request/response models."""

from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field

# UUID fields from SQLAlchemy are returned as uuid.UUID objects.
# This type coerces them to strings during validation (from_attributes mode).
StrUUID = Annotated[str, BeforeValidator(lambda v: str(v) if isinstance(v, UUID) else v)]


# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class PhotoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: StrUUID
    tg_file_id: str
    created_at: datetime


class VoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: StrUUID
    item_id: StrUUID
    user_tg_id: int
    quantity: int


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: StrUUID
    name: str
    price: float  # Decimal -> float
    quantity: int
    votes: list[VoteOut] = []


class MemberOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: StrUUID
    user_tg_id: int
    display_name: str
    tip_percent: int | None
    confirmed: bool
    joined_at: datetime


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: StrUUID
    admin_tg_id: int
    invite_code: str
    status: str
    currency: str
    tip_percent: int
    created_at: datetime
    closed_at: datetime | None = None
    photos: list[PhotoOut] = []
    items: list[ItemOut] = []
    members: list[MemberOut] = []


class SessionBrief(BaseModel):
    id: str
    invite_code: str
    status: str
    created_at: datetime
    member_count: int
    item_count: int


class OcrItemOut(BaseModel):
    name: str
    price: float
    quantity: int


class OcrResultOut(BaseModel):
    items: list[OcrItemOut]
    total: float
    currency: str
    total_mismatch: bool = False


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


# ---------------------------------------------------------------------------
# Request schemas
# ---------------------------------------------------------------------------


class VoteIn(BaseModel):
    item_id: str


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
    currency: str = Field(default="RUB", max_length=8)
