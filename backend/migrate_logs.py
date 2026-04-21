import asyncio
from sqlalchemy import text
from database import engine

async def migrate():
    async with engine.begin() as conn:
        try:
            await conn.execute(text("ALTER TABLE usage_logs ADD COLUMN duration FLOAT DEFAULT 0.0"))
            print("Successfully added duration column to usage_logs.")
        except Exception as e:
            print(f"Migration: {e}")

if __name__ == "__main__":
    asyncio.run(migrate())
