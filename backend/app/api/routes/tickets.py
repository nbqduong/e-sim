from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import (
    get_current_user,
    get_optional_current_user,
    get_ticket_repo,
    get_user_repo,
)
from app.models.ticket import Ticket
from app.models.user import User
from app.repositories.ticket_repo import TicketRepository
from app.repositories.user_repo import UserRepository
from app.schemas.ticket import (
    TicketCreateRequest,
    TicketListResponse,
    TicketResponse,
    TicketUpdateRequest,
    TicketVoteResponse,
)
from app.services.session_manager import SessionData

router = APIRouter(prefix="/api/tickets", tags=["tickets"])


def build_ticket_response(
    ticket: Ticket,
    *,
    viewer: User | None,
    voted_ticket_ids: set[uuid.UUID] | None = None,
) -> TicketResponse:
    voted_ids = voted_ticket_ids or set()
    can_manage = viewer is not None and (viewer.is_admin or ticket.user_id == viewer.id)
    return TicketResponse(
        id=ticket.id,
        user_id=ticket.user_id,
        title=ticket.title,
        description=ticket.description,
        vote_count=ticket.vote_count,
        owner_email=ticket.owner.email,
        owner_display_name=ticket.owner.display_name,
        created_at=ticket.created_at,
        updated_at=ticket.updated_at,
        has_voted=ticket.id in voted_ids,
        can_manage=can_manage,
    )


async def resolve_viewer(
    session_data: SessionData | None,
    user_repo: UserRepository,
) -> User | None:
    if session_data is None:
        return None
    return await user_repo.get_by_id(uuid.UUID(session_data.user_id))


async def require_viewer(
    session_data: SessionData,
    user_repo: UserRepository,
) -> User:
    viewer = await user_repo.get_by_id(uuid.UUID(session_data.user_id))
    if viewer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return viewer


def ensure_ticket_manage_permission(ticket: Ticket, viewer: User) -> None:
    if viewer.is_admin or ticket.user_id == viewer.id:
        return
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="You do not have access to manage this ticket")


@router.get("/", response_model=TicketListResponse)
async def list_tickets(
    session_data: SessionData | None = Depends(get_optional_current_user),
    ticket_repo: TicketRepository = Depends(get_ticket_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> TicketListResponse:
    viewer = await resolve_viewer(session_data, user_repo)
    tickets = await ticket_repo.list()
    voted_ticket_ids = set()
    if viewer is not None:
        voted_ticket_ids = await ticket_repo.get_voted_ticket_ids(
            user_id=viewer.id,
            ticket_ids=[ticket.id for ticket in tickets],
        )

    return TicketListResponse(
        tickets=[
            build_ticket_response(ticket, viewer=viewer, voted_ticket_ids=voted_ticket_ids)
            for ticket in tickets
        ]
    )


@router.get("/{ticket_id}", response_model=TicketResponse)
async def get_ticket(
    ticket_id: uuid.UUID,
    session_data: SessionData | None = Depends(get_optional_current_user),
    ticket_repo: TicketRepository = Depends(get_ticket_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> TicketResponse:
    viewer = await resolve_viewer(session_data, user_repo)
    ticket = await ticket_repo.get_by_id(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    voted_ticket_ids = set()
    if viewer is not None:
        voted_ticket_ids = await ticket_repo.get_voted_ticket_ids(user_id=viewer.id, ticket_ids=[ticket.id])

    return build_ticket_response(ticket, viewer=viewer, voted_ticket_ids=voted_ticket_ids)


@router.post("/", response_model=TicketResponse, status_code=status.HTTP_201_CREATED)
async def create_ticket(
    payload: TicketCreateRequest,
    session_data: SessionData = Depends(get_current_user),
    ticket_repo: TicketRepository = Depends(get_ticket_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> TicketResponse:
    viewer = await require_viewer(session_data, user_repo)
    ticket = await ticket_repo.create(
        user_id=viewer.id,
        title=payload.title,
        description=payload.description,
    )
    return build_ticket_response(ticket, viewer=viewer)


@router.put("/{ticket_id}", response_model=TicketResponse)
async def update_ticket(
    ticket_id: uuid.UUID,
    payload: TicketUpdateRequest,
    session_data: SessionData = Depends(get_current_user),
    ticket_repo: TicketRepository = Depends(get_ticket_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> TicketResponse:
    viewer = await require_viewer(session_data, user_repo)
    ticket = await ticket_repo.get_by_id(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    ensure_ticket_manage_permission(ticket, viewer)
    updated_ticket = await ticket_repo.update(
        ticket,
        title=payload.title,
        description=payload.description,
    )
    voted_ticket_ids = await ticket_repo.get_voted_ticket_ids(user_id=viewer.id, ticket_ids=[updated_ticket.id])
    return build_ticket_response(updated_ticket, viewer=viewer, voted_ticket_ids=voted_ticket_ids)


@router.delete("/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ticket(
    ticket_id: uuid.UUID,
    session_data: SessionData = Depends(get_current_user),
    ticket_repo: TicketRepository = Depends(get_ticket_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> None:
    viewer = await require_viewer(session_data, user_repo)
    ticket = await ticket_repo.get_by_id(ticket_id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    ensure_ticket_manage_permission(ticket, viewer)
    await ticket_repo.delete(ticket)


@router.post("/{ticket_id}/upvote", response_model=TicketVoteResponse)
async def upvote_ticket(
    ticket_id: uuid.UUID,
    session_data: SessionData = Depends(get_current_user),
    ticket_repo: TicketRepository = Depends(get_ticket_repo),
    user_repo: UserRepository = Depends(get_user_repo),
) -> TicketVoteResponse:
    viewer = await require_viewer(session_data, user_repo)
    ticket, created_new_vote = await ticket_repo.add_vote(ticket_id=ticket_id, user_id=viewer.id)
    if ticket is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ticket not found")

    return TicketVoteResponse(
        ticket_id=ticket.id,
        vote_count=ticket.vote_count,
        has_voted=True,
        created_new_vote=created_new_vote,
    )
