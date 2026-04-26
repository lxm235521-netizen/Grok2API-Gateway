import time
import httpx
import json
import random
import re
from datetime import datetime
from fastapi import APIRouter, Request, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from database import AsyncSessionLocal
import models

from models import get_beijing_time

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
                details=details,
                request_time=get_beijing_time() # 强制记录北京时间
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
    content_type = request.headers.get("Content-Type", "").lower()
    is_video = False
    video_prompt = ""
    try:
        if request.method == "POST":
            # 路径包含 video 关键字
            if "video" in path.lower(): 
                is_video = True
            
            # 判定是否为视频生成请求 (支持 JSON 和 Form-data 两种方式)
            if "application/json" in content_type:
                js = json.loads(body.decode("utf-8", errors="ignore"))
                if js.get("model") == "grok-imagine-1.0-video": 
                    is_video = True
                    video_prompt = js.get("prompt", "")
            
            elif "multipart/form-data" in content_type:
                # 寻找 model 和 prompt 字段
                if b'name="model"' in body and b"grok-imagine-1.0-video" in body:
                    is_video = True
                    # 提取 prompt 用于日志
                    prompt_match = re.search(rb'name="prompt"\r\n\r\n(.*?)\r\n--', body, re.DOTALL)
                    if prompt_match:
                        video_prompt = prompt_match.group(1).decode("utf-8", errors="ignore")
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

    # Use client-level timeout; avoid passing timeout= to .send() for httpx compatibility.
    client = httpx.AsyncClient(timeout=None)
    try:
        req = client.build_request(method=request.method, url=target_url, headers=headers, content=body)
        
        # 视频请求采用非流式处理（根据用户新要求）
        if is_video:
            try:
                # 视频生成增加 500s 超时控制（通过 request() 设置，避免 send(timeout=...) 兼容性问题）
                response = await client.request(
                    method=request.method,
                    url=target_url,
                    headers=headers,
                    content=body,
                    timeout=500.0,
                )
                
                # 增加对空响应和异常 JSON 的保护
                try:
                    resp_data = response.json()
                except Exception as e:
                    resp_text = response.text
                    duration = time.time() - start_time
                    await refund_quota(incoming_key, quota)
                    error_detail = f"JSON Decode Error: {str(e)} | Raw Response: {resp_text[:500]}"
                    await record_log(key_id, target_server.url, False, quota, duration, error_detail)
                    return JSONResponse(
                        content={"error": "Upstream returned non-JSON response", "detail": error_detail},
                        status_code=502
                    )

                duration = time.time() - start_time
                
                # 校验逻辑：status == completed 且有视频链接
                video_url = resp_data.get("url", "")
                video_status = resp_data.get("status", "")
                
                # 严格校验：必须 status == completed
                success = response.status_code < 400 and video_status == "completed" and bool(video_url)
                
                if not success:
                    await refund_quota(incoming_key, quota)
                
                # 更新最后使用时间
                async with AsyncSessionLocal() as db_time:
                    await db_time.execute(
                        update(models.APIKey)
                        .where(models.APIKey.id == key_id)
                        .values(last_used_at=get_beijing_time())
                    )
                    await db_time.commit()
                
                await record_log(key_id, target_server.url, success, quota, duration, f"Prompt: {video_prompt} | URL: {video_url or json.dumps(resp_data)}")
                
                # 注入余额 Header 并返回
                resp_headers = dict(response.headers)
                resp_headers["X-Remaining-Quota"] = f"{remaining_quota:.2f}"
                return JSONResponse(content=resp_data, status_code=response.status_code, headers=resp_headers)

            except httpx.TimeoutException:
                duration = time.time() - start_time
                await refund_quota(incoming_key, quota)
                await record_log(key_id, target_server.url, False, quota, duration, "Request timeout (500s)")
                return JSONResponse(
                    content={"error": "Video generation timeout", "detail": "Request exceeded 500 seconds"},
                    status_code=504
                )
            finally:
                await client.aclose()

        # 非视频请求保持流式
        response = await client.send(req, stream=True)
        async def stream_generator():
            full_text = ""
            try:
                async for chunk in response.aiter_bytes():
                    yield chunk
            except Exception as e:
                full_text += f"\n[Gateway Error: {str(e)}]"
            finally:
                await client.aclose()
                duration = time.time() - start_time
                success = response.status_code < 400
                await record_log(key_id, target_server.url, success, 0, duration, full_text[-500:])

        resp_headers = dict(response.headers)
        resp_headers["X-Remaining-Quota"] = f"{remaining_quota:.2f}"
        return StreamingResponse(stream_generator(), status_code=response.status_code, headers=resp_headers)

    except Exception as e:
        await client.aclose()
        duration = time.time() - start_time
        if is_video: await refund_quota(incoming_key, quota)
        await record_log(key_id, target_server.url, False, quota, duration, str(e))
        raise HTTPException(status_code=500, detail=str(e))
