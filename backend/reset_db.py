import asyncio
from sqlalchemy import text
from database import engine, AsyncSessionLocal
from models import Base, User
from auth import get_password_hash

async def reset_and_init():
    async with engine.begin() as conn:
        print("Dropping all tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Creating all tables...")
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        print("Creating super admin...")
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
    asyncio.run(reset_and_init())
