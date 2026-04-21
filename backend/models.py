from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

class Base(DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20), default="admin")  # super_admin, admin
    balance: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    keys = relationship("APIKey", back_populates="owner", cascade="all, delete-orphan")

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    key_value: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    initial_quota: Mapped[float] = mapped_column(Float)
    remaining_quota: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    owner = relationship("User", back_populates="keys")
    logs = relationship("UsageLog", back_populates="api_key", cascade="all, delete-orphan")

class GrokServer(Base):
    __tablename__ = "grok_servers"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    url: Mapped[str] = mapped_column(String(255), unique=True)
    api_key: Mapped[str] = mapped_column(String(255))
    admin_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # 新增管理密码
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)

class UsageLog(Base):
    __tablename__ = "usage_logs"
    
    id: Mapped[int] = mapped_column(primary_key=True)
    key_id: Mapped[int] = mapped_column(ForeignKey("api_keys.id", ondelete="CASCADE"))
    request_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    grok_server: Mapped[str] = mapped_column(String(255))
    is_success: Mapped[bool] = mapped_column(Boolean)
    quota_consumed: Mapped[float] = mapped_column(Float)
    remaining_snapshot: Mapped[float] = mapped_column(Float)
    duration: Mapped[float] = mapped_column(Float, default=0.0) # 新增耗时字段
    details: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    api_key = relationship("APIKey", back_populates="logs")
