from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.models import User, BiometricData, AuditLog

class UserRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_or_create(self, username: str, role: str = "user") -> User:
        res = await self.session.execute(select(User).where(User.username == username))
        user = res.scalar_one_or_none()
        if user:
            return user
        user = User(username=username, role=role)
        self.session.add(user)
        await self.session.flush()
        return user

class BiometricRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_feature(self, user_id: int, type_: str, enc_blob: bytes) -> None:
        row = BiometricData(user_id=user_id, type=type_, enc_feature_blob=enc_blob)
        self.session.add(row)

class AuditRepo:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def add_log(self, user_id: int, result: str, details: str) -> None:
        row = AuditLog(user_id=user_id, result=result, details=details)
        self.session.add(row)
