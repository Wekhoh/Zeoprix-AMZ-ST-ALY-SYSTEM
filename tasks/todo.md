# Task: 产品化收尾（规则闭环 + 多人协作底座）
## Scope
- Goal: 将系统从“验收导向单机工具”继续推进为“规则闭环完整、多人协作可见可管”的成熟产品雏形。
- In scope:
  - 自动建议 / 人工校准 / 最终结论主语义收口
  - 分析运行快照、词级 diff、汇总 delta、规则解释
  - 工作区协作上下文、成员摘要、最小成员管理能力
  - 后续当前用户上下文与角色门控扩展
- Out of scope:
  - 完整 FastAPI / PostgreSQL / 正式登录系统
  - 完整团队邀请、成员删除、审计日志与企业级权限体系

## Checklist
- [x] Plan approved
- [ ] Implementation completed
- [x] Verification completed
- [ ] Review summary captured

## Review Notes
- Key changes:
  - 已完成 A 主线：分析运行快照、词级变化清单、汇总 delta、规则解释
  - 已完成工作区协作可见化：首页/侧边栏/设置页成员摘要
  - 已完成最小成员管理：管理员可按邮箱添加或更新成员角色
  - 已完成：当前用户上下文显式化与侧边栏身份切换
  - 已完成：upload/review 的 viewer 只读门控与审核页权限提示收尾
  - 正在推进：将角色门控扩展到更多敏感操作入口与当前用户本地切换
- Evidence:
  - 最近全量验证基线：`DEBUG=true pytest -q` => 268 passed, 10 skipped, 2 warnings
  - `analyze_mismatches.py` => campaign 107/107, aggregate 398/398
  - 本批次 viewer 只读门控回归：`pytest -q tests/integration/test_app_navigation.py -k "upload_access_meta or review_access_meta or upload_page_blocks_sensitive_actions_for_viewer or review_page_blocks_sensitive_actions_for_viewer"` => 4 passed
  - 已推送产品化提交：A 主线闭环 + workspace context/member management + current-user switching
- Risks / follow-ups:
  - 当前用户上下文仍默认依赖本地 owner，需要继续显式化
  - viewer/editor 权限尚未覆盖所有敏感入口
  - sidebar theme warning 仍是已知未解问题
