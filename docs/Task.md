# 任务清单 (Task)
# AMZ搜索词分析系统

**版本**: 1.0.0
**创建日期**: 2026-01-10
**作者**: Jack Huang
**状态**: ✅ 已完成

---

## 使用说明

- [x] 表示已完成
- [ ] 表示待完成
- 每个任务完成后勾选checkbox
- 同时更新CHANGELOG.md

---

## Sprint 1: 基础设施（Foundation）

### T01: 创建数据库Schema并初始化

**文件**: `src/data/models.py`, `src/data/db.py`

**描述**: 创建7个数据库表的Schema定义和初始化脚本

**验收标准**:
- [x] products表可创建
- [x] campaigns表可创建
- [x] search_terms表可创建
- [x] rules表可创建
- [x] rule_versions表可创建
- [x] analysis_results表可创建
- [x] action_plans表可创建
- [x] 表间外键关系正确

**测试方案**:
```python
# 运行初始化脚本后检查表是否存在
python -c "from src.data.db import Database; db = Database('test.db'); db.init_schema()"
sqlite3 test.db ".tables"
```

**依赖**: 无

- [x] **T01 完成**

---

### T02: 实现数据库操作模块

**文件**: `src/data/db.py`

**描述**: 实现Database类，提供CRUD操作接口

**验收标准**:
- [x] Database.__init__可连接数据库
- [x] init_schema()可初始化表结构
- [x] save_search_terms()可批量插入
- [x] get_search_terms()可按条件查询
- [x] 支持事务操作

**测试方案**:
```python
# 测试插入和查询
db = Database('test.db')
db.init_schema()
count = db.save_search_terms(sample_df, campaign_id=1)
assert count > 0
results = db.get_search_terms({'campaign_id': 1})
assert len(results) > 0
```

**依赖**: T01

- [x] **T02 完成**

---

### T03: 实现应用配置模块

**文件**: `src/config/settings.py`

**描述**: 从.env加载配置，提供全局配置访问

**验收标准**:
- [x] 可加载GEMINI_API_KEY
- [x] 可加载GEMINI_MODEL
- [x] 可加载DATABASE_PATH
- [x] 可加载DEBUG/LOG_LEVEL
- [x] 缺失必要配置时报错提示

**测试方案**:
```python
from src.config.settings import Settings
settings = Settings()
assert settings.gemini_api_key is not None
assert settings.database_path == "data/db/app.db"
```

**依赖**: 无

- [x] **T03 完成**

---

### T04: 实现基础日志系统

**文件**: `src/config/logger.py`

**描述**: 配置Python logging，支持控制台和文件输出

**验收标准**:
- [x] 日志输出到控制台
- [x] 日志级别可配置
- [x] 日志格式包含时间、级别、模块名
- [x] 可按模块获取logger

**测试方案**:
```python
from src.config.logger import get_logger
logger = get_logger(__name__)
logger.info("测试日志")
logger.error("错误日志")
# 检查控制台输出
```

**依赖**: T03

- [x] **T04 完成**

---

## Sprint 2: 数据处理（Data Processing）

### T05: 实现CSV文件解析器

**文件**: `src/data/parser.py`

**描述**: 解析亚马逊后台导出的CSV文件

**验收标准**:
- [x] 可读取UTF-8编码CSV
- [x] 可读取GBK编码CSV
- [x] 自动检测编码
- [x] 识别亚马逊标准列名
- [x] 返回pandas DataFrame

**测试方案**:
```python
from src.data.parser import FileParser
parser = FileParser()
df = parser.parse(open('test_data/sample.csv', 'rb'))
assert 'Customer Search Term' in df.columns or '客户搜索词' in df.columns
```

**依赖**: T04

- [x] **T05 完成**

---

### T06: 实现Excel文件解析器

**文件**: `src/data/parser.py`

**描述**: 解析.xlsx格式的Excel文件

**验收标准**:
- [x] 可读取.xlsx文件
- [x] 可读取多Sheet（默认第一个）
- [x] 可指定Sheet名称
- [x] 返回pandas DataFrame

**测试方案**:
```python
from src.data.parser import FileParser
parser = FileParser()
df = parser.parse(open('test_data/sample.xlsx', 'rb'))
assert len(df) > 0
```

**依赖**: T05

- [x] **T06 完成**

---

### T07: 实现数据清洗与标准化

**文件**: `src/data/parser.py`

**描述**: 清洗和标准化解析后的数据

**验收标准**:
- [x] 列名映射到标准字段（英文→中文统一）
- [x] 数值类型正确转换（spend、clicks等）
- [x] 空值处理（填充0或标记）
- [x] 去除重复行
- [x] 百分比字符串转数值（如"5.23%"→0.0523）

**测试方案**:
```python
df_cleaned = parser.clean_data(df_raw)
assert df_cleaned['spend'].dtype == 'float64'
assert df_cleaned['clicks'].dtype == 'int64'
assert df_cleaned.isna().sum().sum() == 0
```

**依赖**: T06

- [x] **T07 完成**

---

### T08: 实现数据存储模块

**文件**: `src/data/db.py`

**描述**: 将清洗后的DataFrame存入数据库

**验收标准**:
- [x] 创建产品档案（如不存在）
- [x] 创建广告活动（如不存在）
- [x] 批量插入搜索词记录
- [x] 支持增量导入（不覆盖）
- [x] 返回导入统计

**测试方案**:
```python
from src.data.db import Database
db = Database('test.db')
stats = db.import_data(df_cleaned, product_name="测试产品")
assert stats['inserted'] > 0
```

**依赖**: T02, T07

- [x] **T08 完成**

---

### T09: 实现ASIN层聚合

**文件**: `src/data/aggregator.py`

**描述**: 按ASIN汇总所有搜索词数据

**验收标准**:
- [x] 按ASIN分组
- [x] 汇总花费、点击、订单、销售额
- [x] 计算整体ACOS、ROAS
- [x] 计算平均转化率

**测试方案**:
```python
from src.data.aggregator import DataAggregator
agg = DataAggregator(db)
result = agg.aggregate_by_asin()
assert 'asin' in result.columns
assert 'total_spend' in result.columns
```

**依赖**: T08

- [x] **T09 完成**

---

### T10: 实现广告活动层聚合

**文件**: `src/data/aggregator.py`

**描述**: 按广告活动汇总搜索词数据

**验收标准**:
- [x] 按campaign分组
- [x] 汇总各项指标
- [x] 包含匹配类型信息
- [x] 支持筛选ASIN

**测试方案**:
```python
result = agg.aggregate_by_campaign(asin='B0XXXXXX')
assert 'campaign_name' in result.columns
```

**依赖**: T09

- [x] **T10 完成**

---

### T11: 实现匹配类型层聚合

**文件**: `src/data/aggregator.py`

**描述**: 按匹配类型（close-match/loose-match等）汇总

**验收标准**:
- [x] 按match_type分组
- [x] 汇总各项指标
- [x] 支持筛选ASIN和活动

**测试方案**:
```python
result = agg.aggregate_by_match_type(campaign_id=1)
assert 'match_type' in result.columns
```

**依赖**: T10

- [x] **T11 完成**

---

### T12: 实现关键词层聚合

**文件**: `src/data/aggregator.py`

**描述**: 按搜索词/ASIN汇总（最细粒度）

**验收标准**:
- [x] 按term分组
- [x] 区分keyword/asin类型
- [x] 汇总跨活动数据
- [x] 计算表现指标

**测试方案**:
```python
result = agg.aggregate_by_term()
assert 'term' in result.columns
assert 'term_type' in result.columns
```

**依赖**: T11

- [x] **T12 完成**

---

### T13: 实现跨活动对比分析

**文件**: `src/data/aggregator.py`

**描述**: 对比同一关键词在不同活动中的表现

**验收标准**:
- [x] 输入关键词返回各活动数据
- [x] 标记表现差异
- [x] 识别分歧（同词不同表现）

**测试方案**:
```python
result = agg.cross_campaign_analysis(term='wireless charger')
assert len(result) > 0
assert 'campaign_name' in result.columns
```

**依赖**: T12

- [x] **T13 完成**

---

## Sprint 3: 分析引擎（Analysis Engine）

### T14: 实现规则引擎框架

**文件**: `src/rules/engine.py`

**描述**: 规则引擎核心框架，支持规则加载、匹配、执行

**验收标准**:
- [x] 可加载规则配置
- [x] 按优先级排序规则
- [x] 遍历数据匹配规则
- [x] 记录触发的规则
- [x] 返回分析结果列表

**测试方案**:
```python
from src.rules.engine import RuleEngine
engine = RuleEngine(rules)
results = engine.analyze(df)
assert isinstance(results, list)
```

**依赖**: T13

- [x] **T14 完成**

---

### T15: 实现"高花费零转化"规则

**文件**: `src/rules/keyword_rules.py`

**描述**: 识别花费超阈值但零订单的搜索词

**验收标准**:
- [x] 条件: spend > threshold AND orders == 0
- [x] 建议动作: 精确否定
- [x] 阈值可配置（默认$10）

**测试方案**:
```python
# 测试数据: spend=$15, orders=0
result = engine.analyze(test_df)
assert result[0].suggested_action == '精确否定'
```

**依赖**: T14

- [x] **T15 完成**

---

### T16: 实现"低转化高花费"规则

**文件**: `src/rules/keyword_rules.py`

**描述**: 识别转化率低但花费高的搜索词

**验收标准**:
- [x] 条件: ACOS > threshold AND spend > threshold
- [x] 建议动作: 评估否定/降低出价
- [x] 阈值可配置

**测试方案**:
```python
# 测试数据: ACOS=80%, spend=$20
result = engine.analyze(test_df)
assert '否定' in result[0].suggested_action or '降低' in result[0].suggested_action
```

**依赖**: T15

- [x] **T16 完成**

---

### T17: 实现"高转化"规则

**文件**: `src/rules/keyword_rules.py`

**描述**: 识别高转化率的搜索词

**验收标准**:
- [x] 条件: ACOS < threshold AND orders >= min_orders
- [x] 建议动作: 手动投放
- [x] 阈值可配置

**测试方案**:
```python
# 测试数据: ACOS=15%, orders=5
result = engine.analyze(test_df)
assert result[0].suggested_action == '手动投放'
```

**依赖**: T16

- [x] **T17 完成**

---

### T18: 实现"低相关性"规则

**文件**: `src/rules/keyword_rules.py`

**描述**: 识别与产品不相关的搜索词

**验收标准**:
- [x] 条件: 不在核心关键词列表 AND 需AI判断
- [x] 建议动作: 短语否定
- [x] 触发AI相关性判断

**测试方案**:
```python
# 测试数据: term='iphone cable' (产品是安卓充电器)
result = engine.analyze(test_df)
assert result[0].need_ai_judgment == True
```

**依赖**: T17

- [x] **T18 完成**

---

### T19: 实现"分歧处理"规则

**文件**: `src/rules/keyword_rules.py`

**描述**: 处理同一关键词在不同活动中表现分歧

**验收标准**:
- [x] 检测同词多活动数据
- [x] 计算表现差异
- [x] 标记需要AI决策的情况
- [x] 建议动作: 待AI分析

**测试方案**:
```python
# 测试数据: 同一词在活动A转化好，活动B转化差
result = engine.analyze(test_df)
assert result[0].has_conflict == True
```

**依赖**: T18

- [x] **T19 完成**

---

### T20: 实现竞品ASIN规则

**文件**: `src/rules/asin_rules.py`

**描述**: 识别和处理竞品ASIN

**验收标准**:
- [x] 识别ASIN格式搜索词
- [x] 区分自己ASIN/竞品ASIN
- [x] 分析竞品ASIN表现
- [x] 建议动作: 监控/否定

**测试方案**:
```python
# 测试数据: term='B0COMPETITOR'
result = engine.analyze(test_df)
assert result[0].term_type == 'asin'
```

**依赖**: T19

- [x] **T20 完成**

---

### T21: 实现产品配置模块

**文件**: `src/config/manager.py`

**描述**: 管理产品特定配置（核心关键词、相关性词等）

**验收标准**:
- [x] 创建产品配置
- [x] 更新产品配置
- [x] 获取产品配置
- [x] 配置存储在products表的config字段

**测试方案**:
```python
from src.config.manager import ConfigManager
cm = ConfigManager(db)
cm.update_product_config(product_id=1, config={'core_keywords': ['charger']})
config = cm.get_product_config(product_id=1)
assert 'core_keywords' in config
```

**依赖**: T02

- [x] **T21 完成**

---

### T22: 实现配置版本管理

**文件**: `src/config/manager.py`

**描述**: 规则配置版本控制

**验收标准**:
- [x] 修改规则前自动创建版本
- [x] 记录版本号和描述
- [x] 存储规则快照
- [x] 可查看版本历史

**测试方案**:
```python
version = cm.create_version(product_id=1, description='调整花费阈值')
history = cm.get_version_history(product_id=1)
assert len(history) > 0
```

**依赖**: T21

- [x] **T22 完成**

---

### T23: 实现配置回滚功能

**文件**: `src/config/manager.py`

**描述**: 回滚到指定版本的规则配置

**验收标准**:
- [x] 可回滚到任意历史版本
- [x] 回滚前自动备份当前版本
- [x] 恢复规则生效

**测试方案**:
```python
cm.rollback(product_id=1, version=1)
rules = cm.get_current_rules(product_id=1)
# 验证规则是否恢复
```

**依赖**: T22

- [x] **T23 完成**

---

## Sprint 4: AI集成（AI Integration）

### T24: 实现Gemini API客户端

**文件**: `src/ai/client.py`

**描述**: 封装Gemini API调用

**验收标准**:
- [x] 使用google-genai SDK
- [x] 支持generate方法
- [x] 支持chat方法
- [x] 超时处理（30秒）
- [x] 错误处理和重试

**测试方案**:
```python
from src.ai.client import GeminiClient
client = GeminiClient(api_key=os.getenv('GEMINI_API_KEY'))
response = client.generate('Hello')
assert response is not None
```

**依赖**: T03

- [x] **T24 完成**

---

### T25: 实现AI相关性判断

**文件**: `src/ai/analyzer.py`

**描述**: 使用AI判断关键词与产品的相关性

**验收标准**:
- [x] 输入: 关键词 + 产品上下文
- [x] 输出: {relevance: high/medium/low, reason: str}
- [x] 使用结构化Prompt
- [x] 返回JSON格式

**测试方案**:
```python
from src.ai.analyzer import AIAnalyzer
analyzer = AIAnalyzer(client)
result = analyzer.judge_relevance('wireless charger', {'category': 'electronics'})
assert result['relevance'] in ['high', 'medium', 'low']
```

**依赖**: T24

- [x] **T25 完成**

---

### T26: 实现AI分歧解决

**文件**: `src/ai/analyzer.py`

**描述**: 使用AI分析同一关键词在不同活动中的表现分歧

**验收标准**:
- [x] 输入: 关键词 + 多活动数据
- [x] 分析表现差异原因
- [x] 给出综合建议
- [x] 输出: {suggestion: str, reasoning: str}

**测试方案**:
```python
campaign_data = [
    {'campaign': 'A', 'acos': 0.15, 'orders': 10},
    {'campaign': 'B', 'acos': 0.80, 'orders': 2}
]
result = analyzer.resolve_conflict('wireless charger', campaign_data)
assert 'suggestion' in result
```

**依赖**: T25

- [x] **T26 完成**

---

### T27: 实现AI对话助手

**文件**: `src/ai/chat.py`

**描述**: 实现多轮对话能力

**验收标准**:
- [x] 维护对话历史
- [x] 理解上下文
- [x] 可访问数据库查询
- [x] 返回结构化响应

**测试方案**:
```python
from src.ai.chat import ChatAssistant
assistant = ChatAssistant(client, db)
response = assistant.process_message('哪些词需要否定？', context={})
assert 'response' in response
```

**依赖**: T26

- [x] **T27 完成**

---

### T28: 实现引导式对话功能

**文件**: `src/ai/chat.py`

**描述**: 提供预设选项引导用户操作

**验收标准**:
- [x] 根据上下文生成引导选项
- [x] 选项可点击执行
- [x] 支持自定义输入

**测试方案**:
```python
options = assistant.get_guided_options(context={'page': 'analysis'})
assert len(options) > 0
```

**依赖**: T27

- [x] **T28 完成**

---

### T29: 实现AI洞察报告生成

**文件**: `src/ai/analyzer.py`

**描述**: 生成分析洞察摘要

**验收标准**:
- [x] 汇总分析结果
- [x] 生成可读性强的报告
- [x] 包含关键发现和建议

**测试方案**:
```python
insights = analyzer.generate_insights(analysis_results)
assert len(insights) > 100  # 足够详细
```

**依赖**: T26

- [x] **T29 完成**

---

## Sprint 5: UI与导出（UI & Export）

### T30: 实现Streamlit应用入口

**文件**: `src/app.py`

**描述**: Streamlit主入口，配置页面导航

**验收标准**:
- [x] 可运行 streamlit run src/app.py
- [x] 侧边栏导航可用
- [x] 页面切换正常

**测试方案**:
```bash
streamlit run src/app.py
# 手动验证页面加载
```

**依赖**: T04

- [x] **T30 完成**

---

### T31: 实现首页/仪表盘

**文件**: `src/ui/pages/home.py`

**描述**: 展示关键指标和快速入口

**验收标准**:
- [x] 显示总花费、总订单、整体ACOS
- [x] 显示需处理词数
- [x] 快速操作按钮
- [x] 待办事项提醒

**测试方案**:
```bash
# 手动验证页面内容
```

**依赖**: T30, T09

- [x] **T31 完成**

---

### T32: 实现文件上传页面

**文件**: `src/ui/pages/upload.py`

**描述**: 文件上传和解析预览

**验收标准**:
- [x] 拖拽上传支持
- [x] 显示解析预览
- [x] 显示导入结果统计
- [x] 错误提示友好

**测试方案**:
```bash
# 手动上传测试文件验证
```

**依赖**: T30, T08

- [x] **T32 完成**

---

### T33: 实现搜索词分析页面

**文件**: `src/ui/pages/analysis.py`

**描述**: 核心分析界面

**验收标准**:
- [x] 多维筛选面板
- [x] 数据表格（排序、搜索）
- [x] 批量操作支持
- [x] AI分析结果展示

**测试方案**:
```bash
# 手动验证筛选和展示功能
```

**依赖**: T30, T20

- [x] **T33 完成**

---

### T34: 实现操作清单页面

**文件**: `src/ui/pages/actions.py`

**描述**: 展示待执行的操作清单

**验收标准**:
- [x] 否词清单Tab
- [x] 手动词清单Tab
- [x] 可勾选/取消
- [x] 导出按钮

**测试方案**:
```bash
# 手动验证清单展示和交互
```

**依赖**: T30, T20

- [x] **T34 完成**

---

### T35: 实现系统设置页面

**文件**: `src/ui/pages/settings.py`

**描述**: 规则配置和版本管理

**验收标准**:
- [x] 规则阈值编辑
- [x] 版本历史展示
- [x] 回滚操作
- [x] 产品配置管理

**测试方案**:
```bash
# 手动验证配置修改和回滚
```

**依赖**: T30, T23

- [x] **T35 完成**

---

### T36: 实现AI助手侧边栏

**文件**: `src/ui/sidebar.py`

**描述**: 常驻AI对话侧边栏

**验收标准**:
- [x] 对话输入框
- [x] 消息历史展示
- [x] 引导选项按钮
- [x] 清除对话按钮

**测试方案**:
```bash
# 手动验证对话功能
```

**依赖**: T30, T28

- [x] **T36 完成**

---

### T37: 实现否词记录表导出

**文件**: `src/export/exporter.py`

**描述**: 导出需要否定的关键词列表

**验收标准**:
- [x] Excel格式导出
- [x] 包含：关键词、否定类型、触发规则、建议操作
- [x] 文件名包含日期

**测试方案**:
```python
from src.export.exporter import ReportExporter
exporter = ReportExporter()
exporter.export_negative_keywords(results, 'test_negative.xlsx')
# 检查文件是否生成
```

**依赖**: T20

- [x] **T37 完成**

---

### T38: 实现手动词追踪表导出

**文件**: `src/export/exporter.py`

**描述**: 导出推荐手动投放的关键词列表

**验收标准**:
- [x] Excel格式导出
- [x] 包含：关键词、当前表现、建议出价
- [x] 文件名包含日期

**测试方案**:
```python
exporter.export_manual_keywords(results, 'test_manual.xlsx')
# 检查文件是否生成
```

**依赖**: T20

- [x] **T38 完成**

---

### T39: 实现搜索词分析报告导出

**文件**: `src/export/exporter.py`

**描述**: 导出完整分析报告

**验收标准**:
- [x] 多Sheet Excel
- [x] Sheet1: 摘要
- [x] Sheet2: 否词清单
- [x] Sheet3: 手动词清单
- [x] Sheet4: 完整数据

**测试方案**:
```python
exporter.export_analysis_report(results, ai_summary, 'test_report.xlsx')
# 检查文件和Sheet
```

**依赖**: T37, T38

- [x] **T39 完成**

---

### T40: 集成测试

**文件**: `tests/integration/test_workflow.py`

**描述**: 测试核心工作流

**验收标准**:
- [x] 上传→解析→存储流程
- [x] 聚合→规则分析流程
- [x] AI分析流程（可mock）
- [x] 导出流程

**测试方案**:
```bash
pytest tests/integration/ -v
```

**依赖**: T39

- [x] **T40 完成**

---

### T41: 端到端测试

**文件**: `tests/integration/test_e2e.py`

**描述**: 完整用户场景测试

**验收标准**:
- [x] 模拟完整用户操作流程
- [x] 从上传到导出
- [x] 验证输出正确性

**测试方案**:
```bash
pytest tests/integration/test_e2e.py -v
```

**依赖**: T40

- [x] **T41 完成**

---

## 进度统计

| Sprint | 任务数 | 已完成 | 完成率 |
|--------|--------|--------|--------|
| Sprint 1 | 4 | 4 | 100% |
| Sprint 2 | 9 | 9 | 100% |
| Sprint 3 | 10 | 10 | 100% |
| Sprint 4 | 6 | 6 | 100% |
| Sprint 5 | 12 | 12 | 100% |
| **总计** | **41** | **41** | **100%** |

---

## 相关文档

- [Plan.md](Plan.md) - 开发计划
- [PRD.md](PRD.md) - 产品需求文档
- [Design.md](Design.md) - 技术设计文档

---

**文档状态**: ✅ 已完成
**下一步**: 应用已就绪，可通过 start.bat 启动
