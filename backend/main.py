from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

import models
import schemas
import auth
import crud
import gateway
from database import engine, AsyncSessionLocal, get_db, settings

app = FastAPI(title="Grok2API Distribution Gateway")

# 包含路由
app.include_router(crud.router, prefix="/api/admin", tags=["Admin"])
app.include_router(gateway.router, prefix="/proxy/v1", tags=["Gateway"])

@app.post("/token", response_model=schemas.Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.User).filter(models.User.username == form_data.username))
    user = result.scalar_one_or_none()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/api/admin/me", response_model=schemas.UserResponse)
async def get_me(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@app.get("/api/v1/query/{key_value}")
async def query_quota(key_value: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(models.APIKey).filter(models.APIKey.key_value == key_value))
    api_key = result.scalar_one_or_none()
    if not api_key:
        raise HTTPException(status_code=404, detail="Key not found")
    return {
        "key": api_key.key_value[:10] + "****", # 脱敏处理
        "remaining_quota": api_key.remaining_quota,
        "is_active": api_key.is_active,
        "last_used_at": api_key.last_used_at
    }

@app.get("/")
async def root():
    return {"message": "Grok2API Gateway is running"}

# 启动脚本中应包含数据库初始化逻辑
