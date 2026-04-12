# Task: 产品化收尾（规则闭环 + 主链稳定 + AI 审核增强）
## Scope
- Goal: 将系统从“验收导向单机工具”继续推进为“规则闭环完整、主链状态清晰、AI 审核建议更可靠”的成熟产品雏形。
- In scope:
  - 自动建议 / 人工校准 / 最终结论主语义收口
  - 分析运行快照、词级 diff、汇总 delta、规则解释
  - 上传→分析主链状态边界收口
  - AI 审核建议的持久化 / 重试 / 失败体验
  - 新前端工作台壳的视觉重构与信息层级收敛
- Out of scope:
  - 完整 FastAPI / PostgreSQL / 正式登录系统
  - 完整团队邀请、审计日志与企业级权限体系

## Checklist
- [x] Plan approved
- [x] Implementation completed
- [x] Verification completed
- [x] Review summary captured

## Review Notes
- Key changes:
  - 已完成：AI 审核建议的理由 / 建议动作落库与回显
  - 已完成：AI 失败 / 重试 / 空态提示稳定化
  - 已完成：上传成功 ≠ 分析成功，upload/settings_data 已统一状态反馈
  - 已完成：成功分析后持久化运行快照，供“最近一次有效分析结果”复用
  - 已完成：成熟化工作台首页、执行批次、复盘预览与模板中心
  - 已完成：独立前端壳首版改成白底、轻边框、低噪音的 Vercel 风格工作台，并收敛首页信息密度与 typography
- Evidence:
  - 最近全量验证基线：`python -m pytest -q` => 381 passed, 10 skipped, 2 warnings
  - 新前端验证：`cd frontend && npm run build` => passed；`npm run lint` => passed
  - 浏览器快照：`tasks/frontend-home-v2.png` 显示白底、轻卡片、单内容 Tabs 模板中心与更克制的首页层级
- Risks / follow-ups:
  - 新前端仍是独立壳首版，核心业务 API 还未完全接通
  - 如果继续精修 UI，下一步应优先做“首页首屏减法”，不要同时扩更多功能
  - Streamlit 旧前端与新前端壳当前并行存在，需要后续决定切换策略

- 2026-04-11: 新前端继续做 typography 精修：接入 Sora + Instrument Sans 双字体组合，收敛 H1/H2/H3 比例，弱化过粗标题并强化数据数字识别，预览地址更新到 http://127.0.0.1:3005。
