import asyncio
from sqlalchemy import select
from database import engine, AsyncSessionLocal
import models

async def check_readiness():
    async with AsyncSessionLocal() as session:
        # Check servers
        server_result = await session.execute(select(models.GrokServer).filter(models.GrokServer.is_active == True))
        servers = server_result.scalars().all()
        print(f"Active servers: {len(servers)}")
        for s in servers:
            print(f" - {s.name}: {s.url}")

        # Check API Keys
        key_result = await session.execute(select(models.APIKey).filter(models.APIKey.is_active == True))
        keys = key_result.scalars().all()
        print(f"Active API Keys: {len(keys)}")
        for k in keys:
            print(f" - Key ID {k.id}: {k.key_value} (Quota: {k.remaining_quota})")

if __name__ == "__main__":
    asyncio.run(check_readiness())
