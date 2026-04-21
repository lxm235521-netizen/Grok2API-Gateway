import asyncio
from sqlalchemy import text
from database import engine

async def check_schema():
    async with engine.connect() as conn:
        try:
            result = await conn.execute(text("SELECT admin_password FROM grok_servers LIMIT 1"))
            print("Schema check passed: admin_password exists.")
        except Exception as e:
            print(f"Schema check failed: {e}")

if __name__ == "__main__":
    asyncio.run(check_schema())
