# Task: 产品化收尾（规则闭环 + 主链稳定 + AI 审核增强）
## Scope
- Goal: 将系统从“验收导向单机工具”继续推进为“规则闭环完整、主链状态清晰、AI 审核建议更可靠”的成熟产品雏形。
- In scope:
  - 自动建议 / 人工校准 / 最终结论主语义收口
  - 分析运行快照、词级 diff、汇总 delta、规则解释
  - 上传→分析主链状态边界收口
  - AI 审核建议的持久化 / 重试 / 失败体验
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
  - 正在推进：将汇总 / 活动 / ASIN / 操作清单统一到最近一次有效分析结果读取
- Evidence:
  - 最近全量验证基线：`python -m pytest -q` => 323 passed, 10 skipped, 2 warnings
  - `analyze_mismatches.py` => campaign 107/107, aggregate 398/398
  - AI 审核建议状态回归：`python -m pytest -q tests/unit/test_manual_review_relevance.py -k "save_manual_review_ai_suggestion_persists_status_payload or build_ai_request_state or reads_retry_metadata"` => 4 passed
  - 上传→分析状态回归：`python -m pytest -q tests/integration/test_app_navigation.py -k "analysis_run_state_tracks_counts_and_retry_flags or run_analysis_returns_warning_when_no_aggregated_terms or run_analysis_returns_warning_when_engine_produces_no_suggestions or run_analysis_persists_snapshot_on_success or run_analysis_warning_does_not_persist_snapshot"` => 5 passed
  - 最新评估：`python scripts/evaluate_product.py --llm-score workspace=97 --llm-score permissions=97 --llm-score analysis=97 --llm-score governance=97 --change-note "迭代18：成功分析后持久化 snapshot，统一最近一次有效分析结果来源"` => objective 99.50 / llm avg 97.00 / total 98.50
  - 已推送最近提交：`c3405c5 feat: stabilize review ai retry feedback`、`a677670 feat: clarify upload-to-analysis run states`
- Risks / follow-ups:
  - 分析页 / 操作清单仍需进一步统一到最近一次有效分析结果
  - 上传与分析结果的单一可信来源仍在持续收口
  - sidebar theme warning 仍是已知未解问题
  - AI 侧边栏与浮动聊天入口仍需继续观察是否要做流式输出与更强的历史持久化，但当前滚动、等待与重试体验已统一

- 2026-03-30: 已完成汇总页优先读取最近一次有效分析快照，并统一 truth-first / snapshot / realtime 的渲染入口。
- 2026-03-30: 验证补充：快照汇总回归 5 passed；全量 pytest 326 passed, 10 skipped, 2 warnings；评估 objective 99.50 / llm avg 97.00 / total 98.50。
- 2026-04-01: 已完成操作清单优先读取最近一次有效分析快照；无人工真值时，侧边栏执行数量、动作列表与导出结果都优先复用最近一次有效 snapshot，而不是退回实时分析。
- 2026-04-01: 验证补充：操作清单快照回归 6 passed；全量 pytest 330 passed, 10 skipped, 2 warnings；评估 objective 99.50 / llm avg 97.00 / total 98.50。
- 2026-04-01: 已完成 snapshot 行字段扩展，成功分析后会保留 campaign_id / campaign_name / auto_action / confidence / cvr / acos 等维度，并让按活动页在无 truth-first 时优先读取最近一次有效分析快照。
- 2026-04-01: 验证补充：按活动 snapshot 回归 5 passed；全量 pytest 333 passed, 10 skipped, 2 warnings；评估 objective 99.50 / llm avg 97.00 / total 98.50。
- 2026-04-01: 已完成按 ASIN 页优先读取最近一次有效分析快照；无人工真值时，按 ASIN 结果会优先复用最近一次成功分析留下的 snapshot，而不是直接退回实时分析。
- 2026-04-01: 验证补充：按 ASIN snapshot 回归 2 passed；全量 pytest 335 passed, 10 skipped, 2 warnings；评估 objective 99.50 / llm avg 97.00 / total 98.50。
- 2026-04-01: 已完成 AI 侧边栏 / 浮动聊天入口的成熟聊天窗收口：统一消息渲染内核、固定输入区、可滚动消息区、等待思考态、错误/重试提示。
- 2026-04-01: 验证补充：AI 聊天状态定向回归 3 passed；真实浏览器验收确认消息区可滚动、发送后出现“AI 正在思考...”且输入禁用；全量 pytest 338 passed, 10 skipped, 2 warnings；评估 objective 99.50 / llm avg 97.00 / total 98.50。
- 2026-04-01: 已修正 AI 助手弹层在受限视口下把输入区裁掉的问题：空态、快捷提问和历史消息现在统一收进固定高度滚动面板，popover 本体允许纵向滚动，确保输入区始终可见。
- 2026-04-01: 验证补充：受限视口（384x768）浏览器快照确认 AI 助手中可同时看到快捷提问、动作按钮、输入框与免责声明；相关定向回归继续通过。

- 2026-04-01: 修正 AI 助手空态布局，空白对话时隐藏操作栏并缩短空态滚动区高度，确保输入框首屏可见。
- 2026-04-01: 正在修正 AI 助手“只能单轮对话”的连续对话体验：已有消息后输入框需要保持在首屏，动作按钮下移为次级操作，并用真实 Gemini 连发消息做端到端验证。
- 2026-04-03: 已完成 AI Copilot 第一阶段收口：引入统一的 `AIContextPack` / `AIResponseEnvelope`，侧边栏 AI 助手开始显示上下文标签、结构化结论、依据、建议动作与推荐追问。
- 2026-04-03: 已完成页面内嵌 AI 第一批接入：汇总页增加“AI 汇总简报”卡片，操作清单页增加“AI 执行说明”卡片；两者都优先基于当前产品与最近一次有效分析结果生成结构化摘要。
- 2026-04-03: 验证补充：Copilot 定向回归 5 passed；全量 pytest 345 passed, 10 skipped, 2 warnings；`analyze_mismatches.py` 继续保持 campaign 107/107、aggregate 398/398；评估 objective 99.50 / llm avg 97.00 / total 98.50。
- 2026-04-04: 已完成页面内嵌 AI 第二批接入：按活动页增加“AI 活动解释”卡片、按 ASIN 页增加“AI 归因卡”，审核页增加“AI 审核建议”结构化卡片；三者均统一基于 `AIContextPack` / `AIResponseEnvelope` 构建。
- 2026-04-04: 验证补充：campaign/asin/review AI brief 定向回归 5 passed；全量 pytest 348 passed, 10 skipped, 2 warnings；`analyze_mismatches.py` 继续保持 campaign 107/107、aggregate 398/398；评估 objective 99.50 / llm avg 97.00 / total 98.50。
## 2026-04-04
- 已完成上传页 AI 导入摘要卡接入：基于当前导入批次、产品上下文与分析状态生成结构化下一步建议。
- 已验证 upload AI brief：定向测试 2 passed；全量 pytest 350 passed, 10 skipped, 2 warnings；evaluate_product = 99.50 / 97.00 / 98.50。
- 2026-04-05: 继续推进 AI 融合收尾：为操作清单 AI brief 增加“老板汇报摘要 / 执行备注 / 交接提醒”草稿层，并让侧边栏 Copilot 显示上下文徽标与页面感知快捷提问。
