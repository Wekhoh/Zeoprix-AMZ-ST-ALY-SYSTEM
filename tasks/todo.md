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
- [ ] Implementation completed
- [x] Verification completed
- [ ] Review summary captured

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

- 2026-03-30: 已完成汇总页优先读取最近一次有效分析快照，并统一 truth-first / snapshot / realtime 的渲染入口。
- 2026-03-30: 验证补充：快照汇总回归 5 passed；全量 pytest 326 passed, 10 skipped, 2 warnings；评估 objective 99.50 / llm avg 97.00 / total 98.50。
- 2026-04-01: 已完成操作清单优先读取最近一次有效分析快照；无人工真值时，侧边栏执行数量、动作列表与导出结果都优先复用最近一次有效 snapshot，而不是退回实时分析。
- 2026-04-01: 验证补充：操作清单快照回归 6 passed；全量 pytest 330 passed, 10 skipped, 2 warnings；评估 objective 99.50 / llm avg 97.00 / total 98.50。
- 2026-04-01: 已完成 snapshot 行字段扩展，成功分析后会保留 campaign_id / campaign_name / auto_action / confidence / cvr / acos 等维度，并让按活动页在无 truth-first 时优先读取最近一次有效分析快照。
- 2026-04-01: 验证补充：按活动 snapshot 回归 5 passed；全量 pytest 333 passed, 10 skipped, 2 warnings；评估 objective 99.50 / llm avg 97.00 / total 98.50。
- 2026-04-01: 已完成按 ASIN 页优先读取最近一次有效分析快照；无人工真值时，按 ASIN 结果会优先复用最近一次成功分析留下的 snapshot，而不是直接退回实时分析。
- 2026-04-01: 验证补充：按 ASIN snapshot 回归 2 passed；全量 pytest 335 passed, 10 skipped, 2 warnings；评估 objective 99.50 / llm avg 97.00 / total 98.50。
