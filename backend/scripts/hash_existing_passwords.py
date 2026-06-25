import asyncio

from sqlalchemy import select

from app.db.session import SessionLocal
from app.db.models import User
from app.core.security import hash_password, is_password_hash


async def main():
    checked_count = 0
    updated_count = 0

    async with SessionLocal() as db:
        try:
            result = await db.execute(select(User))
            users = result.scalars().all()

            for user in users:
                checked_count += 1

                stored_value = user.password_hash

                if not stored_value:
                    continue

                if is_password_hash(stored_value):
                    continue

                user.password_hash = hash_password(stored_value)
                updated_count += 1

            if updated_count > 0:
                await db.commit()
            else:
                await db.rollback()

            print(f"Checked users: {checked_count}")
            print(f"Updated users: {updated_count}")

        except Exception as e:
            await db.rollback()
            print("Password hash migration failed.")
            print(type(e).__name__)
            raise


if __name__ == "__main__":
    asyncio.run(main())