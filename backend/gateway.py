import time
import httpx
import json
import random
import re
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database import AsyncSessionLocal
import models

router = APIRouter()

async def refund_quota(key_value: str, amount: float):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(models.APIKey).filter(models.APIKey.key_value == key_value))
        api_key = result.scalar_one_or_none()
        if api_key:
            api_key.remaining_quota += amount
            await db.commit()
            print(f"CRITICAL: Refunded {amount} to key {key_value}")

async def record_log(key_id: int, server_url: str, is_success: bool, quota: float, duration: float, details: str):
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(models.APIKey).filter(models.APIKey.id == key_id))
        api_key = result.scalar_one_or_none()
        if api_key:
            log = models.UsageLog(
                key_id=key_id,
                grok_server=server_url,
                is_success=is_success,
                quota_consumed=quota if is_success else 0,
                remaining_snapshot=api_key.remaining_quota,
                duration=duration,
                details=details
            )
            db.add(log)
            await db.commit()

@router.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def proxy_gateway(path: str, request: Request, authorization: str = Header(None)):
    start_time = time.time()
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    incoming_key = authorization.replace("Bearer ", "")
    body = await request.body()
    
    # 1. Auth & Pre-charge
    is_video = False
    try:
        if request.method == "POST":
            if "video" in path.lower(): is_video = True
            elif "chat/completions" in path.lower():
                js = json.loads(body.decode("utf-8", errors="ignore"))
                if js.get("model") == "grok-imagine-1.0-video": is_video = True
    except: pass

    quota = 1.0 if is_video else 0.0
    
    async with AsyncSessionLocal() as db:
        res = await db.execute(select(models.APIKey).filter(models.APIKey.key_value == incoming_key, models.APIKey.is_active == True).with_for_update())
        api_key = res.scalar_one_or_none()
        if not api_key: raise HTTPException(status_code=401, detail="Key invalid")
        if is_video and api_key.remaining_quota < quota: raise HTTPException(status_code=402, detail="Insufficient balance")
        
        if is_video:
            api_key.remaining_quota -= quota
            await db.commit()
        key_id = api_key.id
        remaining_quota = api_key.remaining_quota  # 记录扣费后的额度

    # 2. Get Server
    async with AsyncSessionLocal() as db:
        srv_res = await db.execute(select(models.GrokServer).filter(models.GrokServer.is_active == True))
        servers = srv_res.scalars().all()
    if not servers:
        if is_video: await refund_quota(incoming_key, quota)
        raise HTTPException(status_code=503, detail="No servers")
    target_server = random.choice(servers)

    # 3. Forward
    headers = dict(request.headers)
    headers.pop("host", None)
    headers.pop("authorization", None)
    headers["Authorization"] = f"Bearer {target_server.api_key}"
    
    clean_path = path.lstrip("/")
    target_url = f"{target_server.url}/{clean_path}" if clean_path.startswith("v1/") else f"{target_server.url}/v1/{clean_path}"

    client = httpx.AsyncClient(timeout=None)
    try:
        req = client.build_request(method=request.method, url=target_url, headers=headers, content=body)
        response = await client.send(req, stream=True)
        
        async def stream_generator():
            video_found = False
            video_url = ""
            full_text = ""
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
                    if is_video and not video_found:
                        decoded = chunk.decode(errors="ignore")
                        full_text += decoded
                        match = re.search(r'https?://[^\s]+\.mp4', full_text)
                        if match:
                            video_found = True
                            video_url = match.group(0)

            except Exception as e:
                full_text += f"\n[Gateway Error: {str(e)}]"
            finally:
                await client.aclose()
                duration = time.time() - start_time
                success = response.status_code < 400 and (not is_video or video_found)
                
                log_details = video_url if video_found else full_text[-1000:]
                if is_video and not video_found:
                    await refund_quota(incoming_key, quota)
                
                # 更新 APIKey 的最后使用时间
                async with AsyncSessionLocal() as db_time:
                    await db_time.execute(
                        update(models.APIKey)
                        .where(models.APIKey.id == key_id)
                        .values(last_used_at=datetime.now())
                    )
                    await db_time.commit()
                
                await record_log(key_id, target_server.url, success, quota, duration, log_details)

        # 注入余额 Header
        resp_headers = dict(response.headers)
        resp_headers["X-Remaining-Quota"] = f"{remaining_quota:.2f}"

        return StreamingResponse(stream_generator(), status_code=response.status_code, headers=resp_headers)

    except Exception as e:
        await client.aclose()
        duration = time.time() - start_time
        if is_video: await refund_quota(incoming_key, quota)
        await record_log(key_id, target_server.url, False, quota, duration, str(e))
        raise HTTPException(status_code=500, detail=str(e))
