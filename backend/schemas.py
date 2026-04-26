from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

class UserBase(BaseModel):
    username: str
    role: str = "admin"

class UserCreate(UserBase):
    password: str
    balance: float = 0.0

class UserUpdateBalance(BaseModel):
    user_id: int
    amount: float

class UserResponse(UserBase):
    id: int
    balance: float
    created_at: datetime
    class Config:
        from_attributes = True

class APIKeyCreate(BaseModel):
    initial_quota: float = Field(..., gt=0)
    note: Optional[str] = None

class APIKeyUpdate(BaseModel):
    quota_change: Optional[float] = None # 正数为增加，负数为减少
    note: Optional[str] = None

class APIKeyResponse(BaseModel):
    id: int
    key_value: str
    initial_quota: float
    remaining_quota: float
    created_at: datetime
    last_used_at: Optional[datetime]
    is_active: bool
    note: Optional[str] = None
    class Config:
        from_attributes = True

class GrokServerBase(BaseModel):
    name: str
    url: str
    api_key: str
    admin_password: Optional[str] = None # 新增管理密码
    is_active: bool = True

class GrokServerUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    api_key: Optional[str] = None
    admin_password: Optional[str] = None
    is_active: Optional[bool] = None

class GrokServerCreate(GrokServerBase):
    pass

class GrokServerResponse(GrokServerBase):
    id: int
    token_count: int = 0
    created_at: datetime
    class Config:
        from_attributes = True

class UsageLogResponse(BaseModel):
    id: int
    request_time: datetime
    grok_server: str
    is_success: bool
    quota_consumed: float
    remaining_snapshot: float
    class Config:
        from_attributes = True
