from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from database import engine
import asyncio

async def upgrade():
    async with engine.begin() as conn:
        try:
            # Postgres 检查列是否存在的方式
            check_sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='api_keys' AND column_name='note';
            """)
            result = await conn.execute(check_sql)
            exists = result.scalar()
            
            if not exists:
                print("Adding 'note' column to 'api_keys' table...")
                await conn.execute(text("ALTER TABLE api_keys ADD COLUMN note VARCHAR(255)"))
                print("Success.")
            else:
                print("Column 'note' already exists.")
        except Exception as e:
            print(f"Error during migration: {e}")

if __name__ == "__main__":
    asyncio.run(upgrade())
