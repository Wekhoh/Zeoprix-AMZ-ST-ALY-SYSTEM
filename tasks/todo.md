# Task: 全站端到端验证与体验修复
## Scope
- Goal: 端到端验证所有核心板块与关键交互，修复导航、数据显示脱节、导出不一致与关键体验问题。
- In scope:
  - 首页、搜索词分析、ASIN分析、操作清单、相关性审核、系统设置、导出链路
  - 侧边栏导航与首页快捷入口交互
  - truth-first 结果与原始报表/广告组人工判定表/最终汇总结论表的对齐
- Out of scope:
  - 非阻断 warning 的全面清理
  - 新功能设计或大规模 UI 重构

## Checklist
- [x] Plan approved
- [x] Implementation completed
- [x] Verification completed
- [x] Review summary captured

## Review Notes
- Key changes:
  - 修复侧边栏需点击两次才跳转的问题
  - 首页快捷按钮改为单击回调导航
  - 修复 pandas/numpy campaign_id 导致的人工审核查询异常
  - 对齐首页/汇总/按活动/操作清单/导出到 truth-first 口径
  - 提升侧边栏层级，避免主内容遮挡点击
  - 首页 `待处理项` 与操作清单改为排除跨ASIN分歧项，避免把冲突词错误导出成可执行否词/手动动作
- Evidence:
  - DEBUG=true pytest -q => 224 passed, 2 warnings
  - analyze_mismatches.py => campaign 107/107, aggregate 398/398
  - 浏览器实测：首页待处理项已收敛到 37/11；操作清单仅保留可执行项（24 精确否定 / 8 词组否定 / 5 ASIN否定 / 9 手动精准 / 2 商品定位）
- Risks / follow-ups:
  - ASIN分析 Top/Bottom / 跨ASIN智能仍是洞察视角而非最终动作真相
  - 仍有 sidebar theme warning 待继续判断是否可通过上游兼容方案消除
