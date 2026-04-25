# src/services/settings_service.md

**Purpose:** 工作区设置服务（成员管理、角色权限、配置管理）。

**Last Updated:** 2026-04-25

## Public Surface

- `SettingsService` — 设置服务主类
- `SettingsService.get_workspace_settings()` — 获取工作区设置
- `SettingsService.update_workspace_settings()` — 更新工作区设置
- `SettingsService.manage_members()` — 管理工作区成员
- `SettingsService.manage_roles()` — 管理成员角色
- `SettingsService.backup_settings()` — 备份设置配置
- `SettingsService.restore_settings()` — 恢复设置配置

## Key Dependencies

1. **src.data.db** — 读写工作区、成员、配置数据
2. **src.backend.database** — 后端用户模型和会话

## Data Touched

**Reads/Writes:**
- `workspaces` — 工作区配置
- `workspace_memberships` — 成员角色
- `users` — 用户信息
- `products` — 产品配置

## Used By

- **src.backend.workbench_payload** — `build_settings_page_payload()` 调用
- **src.backend.app** — 设置更新路由

## Architecture Notes

- **RBAC:** 基于角色的访问控制（admin、editor、viewer）
- **Auditability:** 记录配置变更时间和操作者
- **Validation:** 更新前进行权限检查和数据验证

## External Dependencies

- 无额外外部依赖
