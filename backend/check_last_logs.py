import asyncio
from sqlalchemy import select, desc
from database import AsyncSessionLocal
import models

async def check_logs():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(models.UsageLog).order_by(desc(models.UsageLog.created_at)).limit(5)
        )
        logs = result.scalars().all()
        for log in logs:
            print(f"Time: {log.created_at}, Success: {log.is_success}, Quota: {log.quota_consumed}, Details: {log.details}")

if __name__ == "__main__":
    asyncio.run(check_logs())
