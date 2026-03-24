from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies.auth import require_admin
from app.db.models import User
from app.db.session import get_session
from app.domain.schemas import CreateUserRequest, CreateUserResponse

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/users", response_model=CreateUserResponse)
async def create_user(
    req: CreateUserRequest,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_admin),
) -> CreateUserResponse:
    existing_result = await session.execute(
        select(User).where(User.username == req.username)
    )
    existing_user = existing_result.scalar_one_or_none()

    if existing_user is not None:
        raise HTTPException(status_code=400, detail="USERNAME_ALREADY_EXISTS")

    new_user = User(
        username=req.username,
        password_hash=req.password,
        role=req.role,
        is_active=True,
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    return CreateUserResponse(
        message="USER_CREATED",
        user_id=new_user.user_id,
        username=new_user.username,
        role=new_user.role,
    )