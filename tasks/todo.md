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

- 2026-04-11: 新前端首页继续切换到 Vercel / Next.js 风格：Inter 字体、Hero 网格+柔光、Bento Grid、药丸按钮、Copilot 降噪，稳定预览地址更新到 http://127.0.0.1:3007。

- 2026-04-11: 新前端进一步完成 Vercel 风细节打磨：Trend Pulse 柱状图加粗并统一顶部圆角，Copilot/操作 pills padding 收敛，模板中心 Tabs 改为 segmented control，Structure Lens 轨道与数字对齐继续精修；稳定预览地址更新到 http://127.0.0.1:3008。

- 2026-04-11: 新前端已把 upload / analysis / actions / review / settings 从旧深色卡片文案统一迁回白底规范，稳定预览地址更新到 http://127.0.0.1:3009。

- 2026-04-11: 新前端继续完成按钮/pill padding、Trend Pulse 柱状图、模板中心 segmented control 与 Structure Lens 轨道/数字对齐精修，预览刷新基于最新构建重新发布。
- 2026-04-12: 继续精修新前端侧边 AI 助手：改成更轻的内嵌式 Copilot 卡，加入“当前聚焦”气泡与轻量上下文标签，减少长说明和后台感；最新稳定预览地址为 http://127.0.0.1:3010。

- 2026-04-12: 新前端开始与 FastAPI 融合：新增 /frontend/workbench 聚合接口，首页与共享壳优先从后端拉真数据，后端不可用时自动回退 mock；最新联调预览地址为 http://127.0.0.1:3013（后端 8001）。

- 2026-04-12: 前后端融合继续推进到二级页：upload / analysis / actions / review / settings 新增 page payload，前端页面按页消费真实数据块；联调建议使用后端 8001 + 前端 3013。

- 2026-04-12: 新前端继续推进到写路径第一批：FastAPI 已支持创建执行批次、推进批次状态、提交人工审核；前端 actions/review 已接 client mutation 交互，相关后端单测新增并通过。

- 2026-04-12: 新前端继续补写路径：Upload 页已可直接重跑分析，Settings 页已可直接清空运行数据并导出完整备份。

- 2026-04-12: 新前端继续补写路径第二批：Settings 页已支持恢复完整备份，后端已加入 localhost/127.0.0.1 多端口 CORS 允许列表，供浏览器直接调用写接口。

- 2026-04-12: 新前端继续推进到 Upload 真文件上传：FastAPI 已支持多文件上传并自动建活动/可选自动分析；前端 Upload 页已接 file input + FormData 提交。

- 2026-04-13: 新前端继续推进到 AI 助手多轮对话雏形：新增 /frontend/copilot/chat、右侧 CopilotPanel 多轮消息区，并重新起最新联调环境 8004/3016；同时扩到 Upload 真文件上传与 Settings 恢复完整备份的前端交互。

- 2026-04-13: 新前端继续收口体验层：Actions/Review/Upload/Settings 成功后改用 router.refresh 局部刷新；Analysis 页补了真实筛选交互面板。

- 2026-04-13: 新前端继续推进体验层：Copilot 会话开始做 sessionStorage 级历史保留与推荐动作展示；Actions/Review 改成当前页局部状态更新；Analysis 页继续补了搜索、排序与更完整的筛选控制面板。

- 2026-04-13: 继续收口剩余体验层：Upload/Settings 改成当前页局部状态反馈，Copilot 增加会话保留 + 推荐动作直达追问，Analysis 增加搜索与排序；最新稳定预览切到 http://127.0.0.1:3018（后端 8005）。

- 2026-04-13: 继续收口剩余体验：Upload 接入失败文件反馈与当前页导入日志，Copilot 增加页面动作联动与会话重置，Analysis 新增视角切换（止损/补量/待拍板）；最新稳定预览切到 http://127.0.0.1:3019（后端 8006）。

- 2026-04-13: 继续把剩余体验短板往下推：Upload 增加失败文件反馈与更明确的处理中状态，Copilot 后端返回结构化 actionLinks 并在前端直接联动页面，Analysis 增加视角模式切换；最新稳定预览将切到 3020/8007。

- 2026-04-13: 继续推进体验层：Upload 改成真实上传进度条并补失败文件清单，Copilot 页面联动从前端关键词猜测切到后端结构化 actionLinks；下一步应继续做更细的局部状态更新与更完整 Copilot 动作 schema。

- 2026-04-13: 继续推进剩余体验：Actions/Review 开始记录当前页活动日志，Review 改用 item-key 级移除避免同词误删；后续优先继续做更细的 optimistic update 与主页/二级页联动。

- 2026-04-13: 继续往替代旧系统推进：执行批次开始暴露 itemsPreview 并在前端卡片展示；下一层可继续做主页联动和更细的 optimistic update。

- 2026-04-13: 首页 workbench 继续产品化：后端新增 recentActivity，首页加入最近动态卡；Actions 页暴露 itemsPreview，批次卡可直接看到重点词/action/spend。

- 2026-04-13: 继续把剩余联动往首页收：recentActivity 现在附带 href，首页卡片可直接跳到 Upload/Analysis/Actions/Review；执行批次继续显示 itemsPreview，便于不离页检查批次内容。
