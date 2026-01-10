# ADR-004: 配置版本管理方案

**状态**: 已接受
**日期**: 2026-01-10
**决策者**: Jack Huang

---

## 背景

用户需要能够：
1. 调整规则阈值（如花费阈值、转化率阈值）
2. 增加新规则
3. 撤回（回滚）错误的配置修改

这要求系统具备配置版本管理能力。

---

## 决策

**采用数据库快照式版本管理**，在SQLite中存储规则版本历史。

---

## 考虑的选项

### 选项1: 数据库快照式版本管理（已选择）

**实现方式**:
- `rules`表存储当前生效的规则
- `rule_versions`表存储历史版本快照
- 每次修改前自动创建快照

**优点**:
- 实现简单，利用现有数据库
- 查询历史版本方便
- 回滚只需替换rules表数据

**缺点**:
- 版本间差异不直观（需自行对比）

### 选项2: Git式版本管理

**实现方式**:
- 规则存储为JSON文件
- 使用Git跟踪变更

**优点**:
- 天然支持diff和merge
- 完整的变更历史

**缺点**:
- 增加依赖复杂度
- 用户可能不熟悉Git

### 选项3: 事件溯源（Event Sourcing）

**实现方式**:
- 存储每次操作的事件
- 重放事件还原状态

**优点**:
- 完整的审计日志
- 可以重放任意时间点

**缺点**:
- 实现复杂度高
- 对于规则配置来说过度设计

---

## 决策理由

1. **简单直接**: 快照方式对用户来说最容易理解
2. **实现成本低**: 利用现有SQLite，无需额外依赖
3. **满足需求**: 用户只需要"回滚到上一个版本"功能
4. **可扩展**: 未来可升级到更复杂的方案

---

## 技术细节

### 数据库表结构

```sql
-- 规则版本历史表
CREATE TABLE rule_versions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    version INTEGER NOT NULL,
    rules_snapshot JSON NOT NULL,  -- 规则快照
    description TEXT,               -- 版本描述
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

### 版本创建流程

```python
def create_version(product_id: int, description: str) -> int:
    # 1. 获取当前最大版本号
    max_version = get_max_version(product_id)
    new_version = max_version + 1

    # 2. 获取当前规则
    current_rules = get_current_rules(product_id)

    # 3. 创建快照
    snapshot = json.dumps(current_rules)

    # 4. 保存版本
    save_version(product_id, new_version, snapshot, description)

    return new_version
```

### 回滚流程

```python
def rollback(product_id: int, target_version: int) -> None:
    # 1. 创建当前状态的快照（以便反悔）
    create_version(product_id, f"回滚前自动备份")

    # 2. 获取目标版本快照
    snapshot = get_version_snapshot(product_id, target_version)

    # 3. 恢复规则
    restore_rules(product_id, snapshot)
```

### UI设计

```
版本历史
├── v3 (当前) - 2026-01-10 调整花费阈值为$15
├── v2 - 2026-01-09 新增竞品ASIN规则
└── v1 - 2026-01-08 初始配置

[回滚到v2] [对比v2和v3]
```

---

## 业务规则

1. **自动版本创建**: 每次修改规则前自动创建版本
2. **版本描述**: 鼓励用户填写修改说明
3. **保护性快照**: 回滚前自动创建当前版本快照
4. **版本保留**: 保留所有历史版本，不自动删除

---

## 影响

- `rule_versions`表可能随时间增长
- 建议定期清理过旧版本（MVP阶段暂不实现）
- 规则修改操作需要包装在事务中

---

## 相关决策

- [ADR-002: 数据库选择](ADR-002-database.md)
