"""
Seed script — creates an initial admin user.
Run from project root:  python scripts/seed.py
"""
import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from sqlalchemy import select
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.user import Role, User


async def seed():
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == "admin@taskalloc.com"))
        if result.scalar_one_or_none():
            print("✅ Admin user already exists — skipping.")
            return

        admin = User(
            username="admin",
            email="admin@taskalloc.com",
            hashed_password=hash_password("Admin@1234"),
            role=Role.ADMIN,
            is_active=True,
            is_verified=True,
        )
        db.add(admin)
        await db.commit()
        print("✅ Admin user created:")
        print("   Email:    admin@taskalloc.com")
        print("   Password: Admin@1234")
        print("   Role:     ADMIN")
        print("\n⚠️  Change this password immediately after first login!")


if __name__ == "__main__":
    asyncio.run(seed())
