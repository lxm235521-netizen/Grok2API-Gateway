from datetime import datetime
import uuid
import secrets
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func
from typing import List, Optional

import models
import schemas
from database import get_db
from auth import get_current_user, get_super_admin, get_password_hash

router = APIRouter()

# --- Grok2API 集群管理 (超管权限) ---

@router.post("/grok-servers", response_model=schemas.GrokServerResponse)
async def create_grok_server(server_in: schemas.GrokServerCreate, admin: models.User = Depends(get_super_admin), db: AsyncSession = Depends(get_db)):
    db_server = models.GrokServer(**server_in.model_dump())
    db.add(db_server)
    await db.commit()
    await db.refresh(db_server)
    return db_server

@router.get("/grok-servers", response_model=List[schemas.GrokServerResponse])
async def list_grok_servers(admin: models.User = Depends(get_super_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.GrokServer))
    servers = result.scalars().all()
    # 增加默认状态，由前端手动触发检测以提高性能
    for s in servers:
        s.token_count = 0 
    return servers

@router.get("/grok-servers/{server_id}/check")
async def check_grok_server(server_id: int, admin: models.User = Depends(get_super_admin), db: AsyncSession = Depends(get_db)):
    s = await db.get(models.GrokServer, server_id)
    if not s: raise HTTPException(status_code=404, detail="服务器不存在")
    
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            auth_token = s.admin_password or s.api_key
            res = await client.get(f"{s.url}/v1/admin/tokens", headers={"Authorization": f"Bearer {auth_token}"})
            if res.status_code == 200:
                tokens_data = res.json().get("tokens", {})
                count = sum(len(pool) for pool in tokens_data.values())
                return {"status": "success", "token_count": count}
            return {"status": "error", "token_count": -1, "detail": f"状态码 {res.status_code}"}
        except Exception as e:
            return {"status": "error", "token_count": -1, "detail": f"连接失败: {str(e)}"}

@router.get("/dashboard/stats")
async def get_dashboard_stats(current_user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    # 基础查询
    base_query = select(models.UsageLog).filter(models.UsageLog.request_time >= today)
    if current_user.role != "super_admin":
        base_query = base_query.join(models.APIKey).filter(models.APIKey.user_id == current_user.id)
    
    # 基础统计
    total_res = await db.execute(select(func.count()).select_from(base_query.subquery()))
    total_count = total_res.scalar() or 0
    video_res = await db.execute(select(func.count()).select_from(base_query.filter(models.UsageLog.quota_consumed > 0, models.UsageLog.is_success == True).subquery()))
    video_count = video_res.scalar() or 0
    fail_res = await db.execute(select(func.count()).select_from(base_query.filter(models.UsageLog.is_success == False).subquery()))
    fail_count = fail_res.scalar() or 0

    # 服务器统计 (仅超管)
    server_stats = []
    if current_user.role == "super_admin":
        s_query = select(
            models.UsageLog.grok_server,
            func.count(models.UsageLog.id).label("total"),
            func.count(models.UsageLog.id).filter(models.UsageLog.quota_consumed > 0, models.UsageLog.is_success == True).label("video"),
            func.count(models.UsageLog.id).filter(models.UsageLog.is_success == False).label("fail")
        ).filter(models.UsageLog.request_time >= today).group_by(models.UsageLog.grok_server)
        
        s_res = await db.execute(s_query)
        for row in s_res.all():
            server_stats.append({
                "server": row[0],
                "total": row[1],
                "video": row[2],
                "fail": row[3]
            })
    
    return {
        "total_count": total_count,
        "video_count": video_count,
        "fail_count": fail_count,
        "balance": current_user.balance if current_user.role != "super_admin" else -1,
        "server_stats": server_stats
    }

@router.get("/dashboard/logs")
async def get_dashboard_logs(page: int = 1, size: int = 10, current_user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    from sqlalchemy.orm import joinedload
    query = select(models.UsageLog).options(joinedload(models.UsageLog.api_key))
    if current_user.role != "super_admin":
        query = query.join(models.APIKey).filter(models.APIKey.user_id == current_user.id)
    
    total_res = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_res.scalar() or 0
    
    result = await db.execute(query.order_by(models.UsageLog.request_time.desc()).offset((page - 1) * size).limit(size))
    logs = result.scalars().all()
    return {"items": logs, "total": total}

@router.patch("/grok-servers/{server_id}", response_model=schemas.GrokServerResponse)
async def update_grok_server(server_id: int, server_in: schemas.GrokServerUpdate, admin: models.User = Depends(get_super_admin), db: AsyncSession = Depends(get_db)):
    db_server = await db.get(models.GrokServer, server_id)
    if not db_server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    
    update_data = server_in.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_server, key, value)
    
    await db.commit()
    await db.refresh(db_server)
    return db_server

@router.delete("/grok-servers/{server_id}")
async def delete_grok_server(server_id: int, admin: models.User = Depends(get_super_admin), db: AsyncSession = Depends(get_db)):
    server = await db.get(models.GrokServer, server_id)
    if not server:
        raise HTTPException(status_code=404, detail="服务器不存在")
    await db.delete(server)
    await db.commit()
    return {"message": "服务器已移除"}

@router.get("/grok-servers/{server_id}/tokens")
async def get_remote_tokens(server_id: int, admin: models.User = Depends(get_super_admin), db: AsyncSession = Depends(get_db)):
    server = await db.get(models.GrokServer, server_id)
    auth_token = server.admin_password or server.api_key
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{server.url}/v1/admin/tokens", headers={"Authorization": f"Bearer {auth_token}"})
        return res.json()

@router.post("/grok-servers/{server_id}/tokens/clear")
async def clear_remote_tokens(server_id: int, admin: models.User = Depends(get_super_admin), db: AsyncSession = Depends(get_db)):
    server = await db.get(models.GrokServer, server_id)
    auth_token = server.admin_password or server.api_key
    async with httpx.AsyncClient() as client:
        # Grok2API 通过发送空字典更新来清空
        res = await client.post(f"{server.url}/v1/admin/tokens", json={}, headers={"Authorization": f"Bearer {auth_token}"})
        return res.json()

@router.post("/grok-servers/{server_id}/tokens/import")
async def import_remote_tokens(server_id: int, data: dict, admin: models.User = Depends(get_super_admin), db: AsyncSession = Depends(get_db)):
    server = await db.get(models.GrokServer, server_id)
    auth_token = server.admin_password or server.api_key
    async with httpx.AsyncClient() as client:
        res = await client.post(f"{server.url}/v1/admin/tokens", json=data, headers={"Authorization": f"Bearer {auth_token}"})
        return res.json()

@router.post("/users", response_model=schemas.UserResponse)
async def create_user(user_in: schemas.UserCreate, admin: models.User = Depends(get_super_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).filter(models.User.username == user_in.username))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="用户名已注册")
    
    db_user = models.User(
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        role=user_in.role,
        balance=user_in.balance
    )
    db.add(db_user)
    await db.commit()
    await db.refresh(db_user)
    return db_user

@router.get("/users")
async def list_users(page: int = 1, size: int = 10, username: Optional[str] = None, current_user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if current_user.role == "super_admin":
        query = select(models.User)
        if username:
            query = query.filter(models.User.username.contains(username))
        total_res = await db.execute(select(func.count()).select_from(query.subquery()))
        total = total_res.scalar() or 0
        result = await db.execute(query.offset((page - 1) * size).limit(size))
        return {"items": result.scalars().all(), "total": total}
    else:
        return {"items": [current_user], "total": 1}

@router.delete("/users/{user_id}")
async def delete_user(user_id: int, admin: models.User = Depends(get_super_admin), db: AsyncSession = Depends(get_db)):
    if user_id == admin.id:
        raise HTTPException(status_code=400, detail="不能删除当前登录的超级管理员账号")
    
    user = await db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    await db.delete(user)
    await db.commit()
    return {"message": "用户及其关联的所有密钥已成功删除"}

@router.post("/users/add-balance")
async def add_balance(data: schemas.UserUpdateBalance, admin: models.User = Depends(get_super_admin), db: AsyncSession = Depends(get_db)):
    user = await db.get(models.User, data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    
    user.balance += data.amount
    await db.commit()
    return {"message": "余额已更新", "new_balance": user.balance}

# --- 密钥管理 (普管权限) ---

@router.get("/keys/{key_id}/logs")
async def get_key_logs(key_id: int, user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    api_key = await db.get(models.APIKey, key_id)
    if not api_key: raise HTTPException(status_code=404, detail="密钥不存在")
    if user.role != "super_admin" and api_key.user_id != user.id: raise HTTPException(status_code=403, detail="无权访问此密钥")
    log_result = await db.execute(select(models.UsageLog).filter(models.UsageLog.key_id == key_id).order_by(models.UsageLog.request_time.desc()).limit(100))
    return log_result.scalars().all()

@router.get("/users/{user_id}/keys", response_model=List[schemas.APIKeyResponse])
async def get_user_keys(user_id: int, admin: models.User = Depends(get_super_admin), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.APIKey).filter(models.APIKey.user_id == user_id))
    return result.scalars().all()

@router.post("/keys", response_model=schemas.APIKeyResponse)
async def create_key(key_in: schemas.APIKeyCreate, user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    if user.balance < key_in.initial_quota:
        raise HTTPException(status_code=400, detail="账户余额不足，无法创建此额度的密钥")
    user.balance -= key_in.initial_quota
    new_key = models.APIKey(key_value=f"sk-{secrets.token_hex(24)}", user_id=user.id, initial_quota=key_in.initial_quota, remaining_quota=key_in.initial_quota)
    db.add(new_key)
    await db.commit()
    await db.refresh(new_key)
    return new_key

@router.get("/keys")
async def list_keys(page: int = 1, size: int = 10, query: Optional[str] = None, user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    stmt = select(models.APIKey)
    if user.role != "super_admin":
        stmt = stmt.filter(models.APIKey.user_id == user.id)
    
    if query:
        stmt = stmt.filter(models.APIKey.key_value.contains(query))
    
    total_res = await db.execute(select(func.count()).select_from(stmt.subquery()))
    total = total_res.scalar() or 0
    
    result = await db.execute(stmt.order_by(models.APIKey.created_at.desc()).offset((page - 1) * size).limit(size))
    return {"items": result.scalars().all(), "total": total}

@router.delete("/keys/{key_id}")
async def delete_key(key_id: int, user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    api_key = await db.get(models.APIKey, key_id)
    if not api_key: raise HTTPException(status_code=404, detail="密钥不存在")
    if user.role != "super_admin" and api_key.user_id != user.id: raise HTTPException(status_code=403, detail="无权操作此密钥")
    owner = await db.get(models.User, api_key.user_id)
    refund_amount = api_key.remaining_quota
    owner.balance += refund_amount
    await db.delete(api_key)
    await db.commit()
    return {"message": f"密钥已删除，已将 {refund_amount} 额度退回至用户 {owner.username} 账户"}

@router.patch("/keys/{key_id}", response_model=schemas.APIKeyResponse)
async def update_key_quota(key_id: int, update_data: schemas.APIKeyUpdate, user: models.User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    api_key = await db.get(models.APIKey, key_id)
    if not api_key: raise HTTPException(status_code=404, detail="Key not found")
    if user.role != "super_admin" and api_key.user_id != user.id: raise HTTPException(status_code=403, detail="Unauthorized")
    owner = await db.get(models.User, api_key.user_id)
    change = update_data.quota_change
    if change > 0:
        if owner.balance < change: raise HTTPException(status_code=400, detail="账户余额不足")
        owner.balance -= change
        api_key.remaining_quota += change
        api_key.initial_quota += change
    elif change < 0:
        abs_change = abs(change)
        if api_key.remaining_quota < abs_change: raise HTTPException(status_code=400, detail="减少数额不能超过密钥剩余额度")
        api_key.remaining_quota -= abs_change
        api_key.initial_quota -= abs_change
        owner.balance += abs_change
    await db.commit()
    await db.refresh(api_key)
    return api_key
