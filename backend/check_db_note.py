from sqlalchemy import text
from database import engine
import asyncio

async def check():
    async with engine.connect() as conn:
        result = await conn.execute(text("SELECT id, key_value, note FROM api_keys LIMIT 5"))
        for row in result.fetchall():
            print(f"ID: {row[0]}, Key: {row[1][:10]}..., Note: {row[2]}")

if __name__ == "__main__":
    asyncio.run(check())
