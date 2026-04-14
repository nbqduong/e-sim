from __future__ import annotations
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

class UserProfileResponse(BaseModel):
    id: UUID
    email: str
    display_name: str | None
    balance_cents: int = Field(alias="balance")

    model_config = {"from_attributes": True, "populate_by_name": True}

class BalanceTopupRequest(BaseModel):
    amount_cents: int = Field(..., gt=0, description="Amount to add in cents")

class BalanceDeductRequest(BaseModel):
    amount_cents: int = Field(..., gt=0, description="Amount to deduct in cents")

class BalanceResponse(BaseModel):
    new_balance_cents: int
