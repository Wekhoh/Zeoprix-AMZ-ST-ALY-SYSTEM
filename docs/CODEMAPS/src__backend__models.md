# src/backend/models.md

**Purpose:** 后端用户、工作区与成员关系的 SQLAlchemy ORM 模型。

**Last Updated:** 2026-04-25

## Public Surface

- `User` — 后端用户 ORM 模型（id、email、name、password_hash、created_at）
- `Workspace` — 共享工作区 ORM 模型（id、name、created_at）
- `WorkspaceMembership` — 工作区成员关系 ORM 模型（id、workspace_id、user_id、role、created_at）

## Key Dependencies

1. **src.backend.database** — Base (DeclarativeBase)
2. **sqlalchemy** — ORM 框架（Mapped、mapped_column、ForeignKey）

## Data Touched

**Backend Schema tables:**
- `users` — User 对应表
- `workspaces` — Workspace 对应表
- `workspace_memberships` — WorkspaceMembership 对应表（uq_workspace_membership 唯一约束）

## Used By

- **src.backend.database** — `init_backend_schema()` 中显式导入以创建表
- **src.backend.app** — 在 `_get_current_workspace_context()` 等函数中查询这些模型

## Architecture Notes

- **Keys:** 所有表使用 UUID 字符串主键（36 字符）
- **Relationships:** Workspace 与 User 通过 WorkspaceMembership 多对多关联
- **Constraints:** WorkspaceMembership 有 (workspace_id, user_id) 唯一约束，防止重复成员
- **Cascading:** ForeignKey 带 ondelete="CASCADE"，删除 workspace/user 时级联删除 memberships
- **Role:** 默认角色为 "viewer"，支持 admin/editor/viewer 三类

## External Dependencies

- **sqlalchemy** (~2.0) — ORM
