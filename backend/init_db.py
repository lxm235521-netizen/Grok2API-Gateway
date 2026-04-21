import asyncio
from sqlalchemy import text
from database import engine
from models import Base

async def init_db():
    print("Connecting to database at 192.168.153.1:5432...")
    try:
        async with engine.begin() as conn:
            # 检查连接是否可用
            await conn.execute(text("SELECT 1"))
            print("Connection established. Creating tables...")
            await conn.run_sync(Base.metadata.create_all)
        print("Database tables created successfully.")
    except Exception as e:
        print(f"FAILED to initialize database: {e}")

if __name__ == "__main__":
    asyncio.run(init_db())
