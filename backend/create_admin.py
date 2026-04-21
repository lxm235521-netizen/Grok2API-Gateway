import asyncio
from sqlalchemy import select
from database import AsyncSessionLocal
from models import User
from auth import get_password_hash

async def create_admin():
    async with AsyncSessionLocal() as session:
        # 检查是否已存在 admin
        result = await session.execute(select(User).filter(User.username == "admin"))
        if result.scalar_one_or_none():
            print("Admin user already exists.")
            return

        admin = User(
            username="admin",
            hashed_password=get_password_hash("admin123"),
            role="super_admin",
            balance=9999999.0
        )
        session.add(admin)
        await session.commit()
        print("Super admin created: admin / admin123")

if __name__ == "__main__":
    asyncio.run(create_admin())
