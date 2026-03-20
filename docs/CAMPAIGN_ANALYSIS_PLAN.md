# 按广告活动分别分析功能 - 实施计划

**任务**: 让系统支持按广告活动维度分析，同一关键词可有不同建议
**创建日期**: 2026-01-13
**状态**: `Phase 1-4 完成，Phase 5 部分完成（自动化脚本待补充）`

---

## 目标

用户当前工作流：
```
neck pillow 在 DBL-1.88bid → 表现好 → 手动精准 + 自动保留
neck pillow 在 BLK-1.2bid → 表现差 → 手动精准 + 自动否定
```

系统需要支持：
1. **按活动保留数据** - 不再跨活动聚合
2. **多建议输出** - 同一词按活动给不同建议
3. **复合动作** - "手动精准 + 自动保留/否定"

---

## Phase 1: 数据模型扩展 `[x] 完成`

### 1.1 新增 CampaignAnalysisResult (`src/rules/engine.py`)

```python
@dataclass
class CampaignAnalysisResult:
    """按活动分析的结果（保留活动维度）"""
    term: str
    term_type: str
    campaign_id: int
    campaign_name: str
    triggered_rule: str
    suggested_action: str          # 主动作
    auto_action: str               # keep/negate/observe
    action_type: str
    # ... 指标字段
```

### 1.2 ActionType 扩展 (`src/data/models.py`)

已有组合动作类型：
- `MANUAL_EXACT_NO_NEG` - 手动精准+自动先不否
- `MANUAL_EXACT_WITH_NEG` - 手动精准+自动否定
- `MANUAL_PRODUCT_NO_NEG` - 手动商品定位+自动先不否
- `MANUAL_PRODUCT_WITH_NEG` - 手动商品定位+自动否定

---

## Phase 2: 聚合器扩展 `[x] 完成`

### 2.1 新增方法 (`src/data/aggregator.py`)

```python
def aggregate_by_campaign_term(self, product_id=None, term_type=None) -> pd.DataFrame:
    """按活动+关键词聚合，保留活动维度"""
    # 包含 campaign_id 空值验证
```

### 2.2 跨活动对比 (复用现有 `cross_campaign_analysis`)

---

## Phase 3: 规则引擎扩展 `[x] 完成`

### 3.1 新分析模式 (`src/rules/engine.py`)

```python
def analyze_by_campaign(self, df: pd.DataFrame) -> list[CampaignAnalysisResult]:
    """按活动分别应用规则，返回多个结果"""

def analyze_search_terms_by_campaign(db, product_id=None) -> list[CampaignAnalysisResult]:
    """便捷函数：按活动分析搜索词"""
```

### 3.2 复合动作决策逻辑

```python
def _determine_auto_action(self, action_type, clicks, orders, cvr, spend) -> str:
    """决定自动活动中的动作

    逻辑：
    1. 规则指定 WITH_NEG → 直接返回 negate
    2. 规则指定 NO_NEG → 直接返回 keep
    3. 纯手动动作 → 根据表现计算:
       - CVR >= 10% 且 orders >= 1 → keep
       - clicks >= 20 且 orders = 0 → negate
       - 其他 → observe
    """
```

---

## Phase 4: UI 展示改造 `[x] 完成`

### 4.1 新增"按活动分析"视图（已实现）

```
┌─────────────────────────────────────────────────────────────┐
│ 关键词: neck pillow                        [强相关核心词]    │
├─────────────────────────────────────────────────────────────┤
│ 活动                    │ 表现      │ 主动作   │ 自动处理   │
├─────────────────────────┼───────────┼──────────┼────────────┤
│ DBL-SP自动-1.88bid      │ CVR 12%  │ 手动精准 │ [x] 保留   │
│ BLK-SP自动-1.2bid       │ CVR 0%   │ 手动精准 │ [x] 否定   │
│ BLK-SP自动-1.5bid       │ CVR 8%   │ 手动精准 │ [ ] 观察   │
└─────────────────────────┴───────────┴──────────┴────────────┘
```

### 4.2 操作清单改造（部分完成）

- 操作清单仍基于汇总分析结果展示（未按活动分组）
- 复合动作导出格式（按活动/按ASIN在分析页提供CSV导出）
- 人工审核勾选功能位于「搜索词分析」页

---

## Phase 5: 测试与验证 `[x] 部分完成（自动化脚本待补充）`

### 5.1 单元测试 (已完成)
- [x] `_determine_auto_action` 逻辑测试 (8个测试用例)
- [x] 边界条件测试 (CVR=10%, clicks=20)
- [x] 规则优先级测试 (WITH_NEG/NO_NEG 覆盖表现判断)

### 5.2 集成测试 (待补充)
- [ ] 自动化集成测试脚本

### 5.3 待完成
- [ ] UI 集成测试
- [ ] 复合动作导出验证

---

## 文件清单

| 文件 | 改动 | 状态 |
|------|------|------|
| `src/rules/engine.py` | CampaignAnalysisResult, analyze_by_campaign | 完成 |
| `src/data/aggregator.py` | aggregate_by_campaign_term | 完成 |
| `tests/unit/test_sprint3.py` | TestCampaignAnalysis (8个测试) | 完成 |
| `scripts/test_campaign_analysis.py` | 集成测试脚本 | 缺失（未找到文件） |
| `src/ui/pages/analysis.py` | 按活动视图 | 完成 |
| `src/ui/pages/actions.py` | 复合动作导出 | 完成 |

---

## 错误日志

| 错误 | 尝试 | 解决方案 |
|------|------|----------|
| Database() missing db_path | 直接实例化 | 导入 Settings，使用 settings.database_path |
| get_products() not found | 方法名错误 | 改为 get_all_products() |
| KeyError: product_id | 列不存在 | 使用 product_asin 替代 |
| UnicodeEncodeError (emojis) | Windows 控制台编码问题 | 替换 emoji 为 ASCII 文本 |
| auto_action 语义冲突 | WITH_NEG 规则被表现覆盖 | 规则指定策略时直接遵循，不再计算 |

---

## 决策记录

### D1: 是否保留原有聚合分析？
**决策**: 保留，新增按活动分析作为可选模式
**原因**: 向后兼容，用户可选择分析粒度

### D2: 复合动作如何存储？
**决策**: 拆分为 `suggested_action` + `auto_action` 两个字段
**原因**: 更灵活，便于导出时分别处理

### D3: 规则指定策略 vs 表现计算
**决策**: 规则已指定 WITH_NEG/NO_NEG 时直接遵循，不被表现覆盖
**原因**: 尊重规则意图，避免语义冲突

---

## 验证结果（数据库统计）

```
数据库统计（data/db/app.db，product_id=1）:
- 分析记录: 632 条
- 唯一关键词: 316 个
- 唯一活动: 6 个
- 多活动关键词: 93 个
 
备注：自动化测试运行未在本次会话复核。
```
