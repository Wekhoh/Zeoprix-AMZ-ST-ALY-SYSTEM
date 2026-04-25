# src/backend/auth.md

**Purpose:** 后端认证基础（JWT、密码哈希、用户认证）。

**Last Updated:** 2026-04-25

## Public Surface

- `hash_password()` — 使用 bcrypt 哈希明文密码
- `verify_password()` — 校验明文密码与哈希是否匹配
- `create_access_token()` — 创建 JWT access token（默认 30 分钟过期）
- `decode_access_token()` — 解码并验证 JWT token
- `authenticate_user()` — 从数据库按 email + password 认证用户
- `get_current_user_from_token()` — 从 JWT token 提取用户信息
- `issue_access_token_for_user()` — 为用户签发新 token
- `authenticate_bootstrap_user()` — 兼容保留：直接认证环境变量中的 bootstrap admin
- `_get_bootstrap_user()` — 从环境变量读取 bootstrap admin 配置
- `AuthConfigError` — 认证配置缺失异常
- `AuthenticationError` — 认证失败异常
- `JWT_ALGORITHM` — "HS256"（常量）
- `DEFAULT_ACCESS_TOKEN_MINUTES` — 30（常量）

## Key Dependencies

1. **src.backend.database** — SessionFactory 依赖（用于数据库会话）
2. **bcrypt** — 密码哈希库
3. **pyjwt** — JWT token 库

## Data Touched

**Backend Schema (reads only):**
- `users` — 按 email 查询用户以做认证

## Used By

- **src.backend.app** — `oauth2_scheme` 依赖 + `get_current_user()` 依赖
- **src.backend.database** — `init_backend_schema()` 调用 `_get_bootstrap_user()`

## Architecture Notes

- **JWT Secret:** 从 `AMZ_BACKEND_JWT_SECRET` 环境变量读取（缺失则抛 AuthConfigError）
- **Token Expiry:** 默认 30 分钟，可通过 expires_delta 参数自定义
- **Bcrypt rounds:** 使用 bcrypt.gensalt() 默认轮数
- **Bootstrap Admin:** 支持 AMZ_BOOTSTRAP_ADMIN_PASSWORD_HASH 或 AMZ_BOOTSTRAP_ADMIN_PASSWORD（会动态哈希）

## External Dependencies

- **bcrypt** (~4.x) — 密码哈希
- **pyjwt** (~2.x) — JWT
