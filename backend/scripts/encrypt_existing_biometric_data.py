import asyncio

from sqlalchemy import select

from app.core.security import encrypt_feature_blob, is_encrypted_feature_blob
from app.db.models import BiometricData
from app.db.session import SessionLocal


async def main():
    checked_count = 0
    updated_count = 0
    skipped_empty_count = 0
    skipped_encrypted_count = 0

    async with SessionLocal() as db:
        try:
            result = await db.execute(select(BiometricData))
            rows = result.scalars().all()

            for row in rows:
                checked_count += 1

                stored_blob = row.enc_feature_blob

                if not stored_blob:
                    skipped_empty_count += 1
                    continue

                if is_encrypted_feature_blob(stored_blob):
                    skipped_encrypted_count += 1
                    continue

                row.enc_feature_blob = encrypt_feature_blob(stored_blob)
                updated_count += 1

            if updated_count > 0:
                await db.commit()
            else:
                await db.rollback()

            print(f"Checked biometric rows: {checked_count}")
            print(f"Updated biometric rows: {updated_count}")
            print(f"Skipped empty rows: {skipped_empty_count}")
            print(f"Skipped already encrypted rows: {skipped_encrypted_count}")

        except Exception as e:
            await db.rollback()
            print("Biometric encryption migration failed.")
            print(type(e).__name__)
            raise


if __name__ == "__main__":
    asyncio.run(main())