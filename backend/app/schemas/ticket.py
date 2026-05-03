from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class TicketCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)


class TicketUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = Field(default=None, max_length=2000)


class TicketResponse(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    description: str
    vote_count: int
    owner_email: str
    owner_display_name: str | None
    created_at: datetime
    updated_at: datetime
    has_voted: bool = False
    can_manage: bool = False


class TicketListResponse(BaseModel):
    tickets: list[TicketResponse]


class TicketVoteResponse(BaseModel):
    ticket_id: UUID
    vote_count: int
    has_voted: bool
    created_new_vote: bool
