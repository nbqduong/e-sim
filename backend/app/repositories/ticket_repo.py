from __future__ import annotations

import uuid

from sqlalchemy import desc, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.ticket import Ticket
from app.models.ticket_vote import TicketVote


class TicketRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list(self) -> list[Ticket]:
        result = await self._session.execute(
            select(Ticket)
            .options(selectinload(Ticket.owner))
            .order_by(desc(Ticket.vote_count), desc(Ticket.created_at))
        )
        return list(result.scalars().all())

    async def get_by_id(self, ticket_id: uuid.UUID) -> Ticket | None:
        result = await self._session.execute(
            select(Ticket)
            .options(selectinload(Ticket.owner))
            .where(Ticket.id == ticket_id)
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        *,
        user_id: uuid.UUID,
        title: str,
        description: str,
    ) -> Ticket:
        ticket = Ticket(user_id=user_id, title=title, description=description)
        self._session.add(ticket)
        await self._session.flush()
        hydrated_ticket = await self.get_by_id(ticket.id)
        if hydrated_ticket is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Created ticket could not be reloaded")
        return hydrated_ticket

    async def update(
        self,
        ticket: Ticket,
        *,
        title: str | None = None,
        description: str | None = None,
    ) -> Ticket:
        if title is not None:
            ticket.title = title
        if description is not None:
            ticket.description = description
        await self._session.flush()
        hydrated_ticket = await self.get_by_id(ticket.id)
        if hydrated_ticket is None:  # pragma: no cover - defensive guard
            raise RuntimeError("Updated ticket could not be reloaded")
        return hydrated_ticket

    async def delete(self, ticket: Ticket) -> None:
        await self._session.delete(ticket)
        await self._session.flush()

    async def get_voted_ticket_ids(
        self,
        *,
        user_id: uuid.UUID,
        ticket_ids: list[uuid.UUID],
    ) -> set[uuid.UUID]:
        if not ticket_ids:
            return set()

        result = await self._session.execute(
            select(TicketVote.ticket_id).where(
                TicketVote.user_id == user_id,
                TicketVote.ticket_id.in_(ticket_ids),
            )
        )
        return set(result.scalars().all())

    async def add_vote(
        self,
        *,
        ticket_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> tuple[Ticket | None, bool]:
        ticket = await self._session.get(Ticket, ticket_id)
        if ticket is None:
            return None, False

        vote_insert = (
            insert(TicketVote)
            .values(ticket_id=ticket_id, user_id=user_id)
            .on_conflict_do_nothing(index_elements=[TicketVote.ticket_id, TicketVote.user_id])
            .returning(TicketVote.ticket_id)
        )
        result = await self._session.execute(vote_insert)
        inserted = result.scalar_one_or_none() is not None

        if inserted:
            await self._session.execute(
                update(Ticket)
                .where(Ticket.id == ticket_id)
                .values(vote_count=Ticket.vote_count + 1)
            )
            await self._session.flush()

        hydrated_ticket = await self.get_by_id(ticket_id)
        return hydrated_ticket, inserted
