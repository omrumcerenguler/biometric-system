from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.models import User
from app.db.session import get_session

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="MISSING_TOKEN")

    token = credentials.credentials

    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN")

    username = payload.get("sub")
    if not username:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN_PAYLOAD")
    client = payload.get("client")
    if not client:
        raise HTTPException(status_code=401, detail="INVALID_TOKEN_PAYLOAD")

    result = await session.execute(
        select(User).where(
            User.username == username,
            User.client == client,
        )
)
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(status_code=401, detail="USER_NOT_FOUND")

    if not user.is_active:
        raise HTTPException(status_code=401, detail="USER_INACTIVE")

    return user


async def require_admin(
    current_user: User = Depends(get_current_user),
) -> User:
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="INSUFFICIENT_PERMISSIONS")
    return current_user