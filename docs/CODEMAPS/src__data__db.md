# src/data/db.md

**Purpose:** SQLite 数据库操作主类，提供产品、搜索词、规则、执行批次等数据的 CRUD 操作。

**Last Updated:** 2026-04-25

## Public Surface

- `Database` — 主操作类，encapsulates SQLite connection + CRUD 逻辑
- `get_slow_query_stats()` — 返回慢查询聚合统计（count、avg_ms、max_ms）
- `reset_slow_query_stats()` — 清空慢查询统计（测试用）
- `Database.__init__()` — 初始化数据库路径
- `Database.init_schema()` — 创建所有表与默认规则
- `Database.execute()` — 执行单条 SQL（含慢查询追踪）
- `Database.executemany()` — 批量执行 SQL
- `Database.commit()` / `rollback()` / `close()` — 事务控制
- `Database.create_user()` — 创建用户（legacy SQLite 用户）
- `Database.get_user()` — 按 user_id 或 email 查询用户
- `Database.create_product()` — 创建产品（ASIN、name、config）
- `Database.get_product()` / `get_all_products()` — 查询产品
- `Database.update_product()` — 更新产品字段
- `Database.save_search_terms()` — 插入搜索词 DataFrame（批量）
- `Database.get_search_terms()` — 查询搜索词（支持过滤）
- `Database.get_rules()` / `get_all_rules()` — 查询规则
- `Database.create_rule()` — 创建规则（asin 或 keyword 规则）
- `Database.update_rule()` / `delete_rule()` / `toggle_rule()` — 规则修改
- `Database.reset_rules_to_default()` — 恢复默认规则
- `Database.create_rule_version()` / `get_rule_versions()` — 规则版本控制
- `Database.create_campaign()` — 创建广告活动
- `Database.save_strategy_profile()` / `get_strategy_profile()` — 保存/读取策略配置
- `Database.create_execution_batch()` — 创建执行批次

## Key Dependencies

1. **src.data.models** — ALL_SCHEMAS、DEFAULT_RULES、INDEXES 数据库架构定义
2. **src.config.product_defaults** — `build_seeded_product_config()` 初始化产品配置
3. **src.rules.asin_rules** — `is_valid_asin()` 验证 ASIN 格式

## Data Touched

**SQLite Schema (所有核心表):**
- `products` — 产品信息（asin、name、config JSON）
- `search_terms` — 搜索词数据（campaign_id、term、metrics）
- `rules` — 规则引擎规则（type、conditions、actions、enabled）
- `rule_versions` — 规则快照版本控制
- `campaigns` — 广告活动（product_id、name）
- `strategy_profiles` — 配置配置文件（JSON 存储）
- `users` — 用户（legacy）
- `workspace_memberships` — 工作区成员（legacy SQLite）
- `execution_batches` — 执行批次（status、notes）
- `execution_logs` — 执行日志

## Used By

- **src.backend.workbench_payload** — 大量调用 Database 方法读取产品/搜索词/规则
- **src.analysis.asin_analyzer** — 读取产品配置、搜索词数据
- **scripts/** — 数据导入、调试脚本

## Architecture Notes

- **Slow Query Tracking (Sprint 5 C.3):** 每次 execute/executemany 计时，超过阈值（默认 100ms，环境变量 AMZ_DB_SLOW_QUERY_MS 可配）写 WARNING 日志
- **Context Manager:** `with Database(path) as db:` 自动 commit/rollback
- **JSON Storage:** product.config、strategy_profiles 等字段存储 JSON 字符串
- **Batch Operations:** save_search_terms 可一次插入数千条记录
- **Version Control:** rule_version_snapshot 记录规则状态快照供恢复

## External Dependencies

- **sqlite3** — SQLite driver
- **pandas** — DataFrame 用于批量操作
