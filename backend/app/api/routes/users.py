from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user, get_user_repo
from app.repositories.user_repo import UserRepository
from app.schemas.user import (
    UserProfileResponse,
    BalanceTopupRequest,
    BalanceDeductRequest,
    BalanceResponse
)
from app.services.session_manager import SessionData

router = APIRouter(prefix="/api/users", tags=["users"])

@router.get("/me", response_model=UserProfileResponse)
async def get_user_profile(
    current_user: SessionData = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo),
) -> UserProfileResponse:
    user = await user_repo.get_by_id(uuid.UUID(current_user.user_id))
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserProfileResponse.model_validate(user)

@router.post("/me/balance/topup", response_model=BalanceResponse)
async def topup_balance(
    payload: BalanceTopupRequest,
    current_user: SessionData = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo),
) -> BalanceResponse:
    updated_user = await user_repo.add_balance(
        uuid.UUID(current_user.user_id), 
        amount_cents=payload.amount_cents
    )
    if not updated_user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    return BalanceResponse(new_balance_cents=updated_user.balance)

@router.post("/me/balance/deduct", response_model=BalanceResponse)
async def deduct_balance(
    payload: BalanceDeductRequest,
    current_user: SessionData = Depends(get_current_user),
    user_repo: UserRepository = Depends(get_user_repo),
) -> BalanceResponse:
    updated_user = await user_repo.deduct_balance(
        uuid.UUID(current_user.user_id),
        amount_cents=payload.amount_cents
    )
    if not updated_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="Insufficient funds or user not found"
        )
    
    return BalanceResponse(new_balance_cents=updated_user.balance)
