# Grok2API 分发管理网关 - 部署手册

## 1. 快速启动 (Docker)
在项目根目录下执行：
```bash
docker-compose up -d
```

## 2. 初始化超级管理员
首次启动后，需要进入容器创建首个超级管理员：
```bash
docker-compose exec backend python -c "from database import AsyncSessionLocal; from models import User; from auth import get_password_hash; import asyncio; async def init(): async with AsyncSessionLocal() as s: s.add(User(username='admin', hashed_password=get_password_hash('admin123'), role='super_admin', balance=999999)); await s.commit(); asyncio.run(init())"
```

## 3. 核心接口说明
- **管理后台**: `http://localhost`
- **API 代理地址**: `http://localhost:8000/proxy/v1/chat/completions`
- **认证方式**: 在请求头中加入 `Authorization: Bearer sk-xxxxxx` (sk 密钥在后台创建)

## 4. 防漏损设计
- 数据库事务锁：`gateway.py` 使用 `with_for_update` 锁定 API Key 行。
- 额度退回机制：删除密钥时，剩余 `remaining_quota` 自动加回 `User.balance`。
