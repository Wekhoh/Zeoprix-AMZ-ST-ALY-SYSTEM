# AMZ搜索词分析系统

亚马逊北美站FBA卖家的智能搜索词分析工具，帮助优化广告投放、识别高转化词、自动否定低效词。

## 功能特性

### 核心功能
- **文件上传与解析**: 支持亚马逊后台导出的CSV/Excel搜索词报告
- **多维度数据聚合**: ASIN → 广告活动 → 匹配类型 → 关键词 四层聚合
- **规则引擎自动分类**:
  - 高花费零转化词 → 建议否定
  - 高转化词 → 建议手动投放
  - 竞品ASIN → 智能分析
- **AI智能分析**: 基于Google Gemini，判断关键词相关性、解决分歧
- **AI对话助手**: 引导式问答，快速获取分析建议
- **配置版本管理**: 规则阈值可调整、可回滚
- **报告导出**: 否词表、手动词表、完整分析报告

### 技术亮点
- 本地SQLite数据库，数据安全
- Streamlit现代化UI
- 完整的测试覆盖（90+ 测试用例）

## 安装指南

### 环境要求
- Python 3.10+
- pip 包管理器

### 安装步骤

1. **克隆或下载项目**
```bash
cd "你的目录"
git clone <项目地址>
# 或直接下载并解压
```

2. **创建虚拟环境（推荐）**
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

3. **安装依赖**
```bash
pip install -r requirements.txt
```

4. **配置API密钥**
```bash
# 复制示例配置
cp .env.example .env

# 编辑 .env 文件，添加你的 Gemini API Key
# GEMINI_API_KEY=your_api_key_here
```

获取API Key: [Google AI Studio](https://makersuite.google.com/app/apikey)

## 运行指南

### 启动应用
```bash
streamlit run src/app.py
```

应用将在浏览器中打开，默认地址: `http://localhost:8501`

### 运行测试
```bash
# 运行所有测试
python -m pytest tests/ -v

# 运行单元测试
python -m pytest tests/unit/ -v

# 查看测试覆盖率
python -m pytest tests/ -v --cov=src --cov-report=html
```

## 使用说明

### 1. 上传数据

1. 点击左侧导航 **"文件上传"**
2. 选择或创建产品
3. 上传亚马逊搜索词报告（CSV/Excel）
4. 预览数据并确认导入
5. 系统自动运行规则分析

### 2. 查看分析结果

1. 点击 **"搜索词分析"**
2. 使用筛选器过滤结果
3. 查看分类统计和详情
4. 点击 **"AI分析待确认项"** 让AI辅助判断

### 3. 执行操作

1. 点击 **"操作清单"**
2. 查看否词清单和手动投放推荐
3. 复制词表或导出Excel
4. 在亚马逊后台执行操作

### 4. 调整配置

1. 点击 **"系统设置"**
2. 调整规则阈值（如高花费阈值、目标ACOS等）
3. 保存配置
4. 可在版本历史中回滚

### 如何导出亚马逊搜索词报告

1. 登录亚马逊卖家后台
2. 进入 **广告** → **广告活动管理器**
3. 选择要分析的广告活动
4. 点击 **搜索词** 标签
5. 选择日期范围（建议30天或更长）
6. 点击 **导出** 按钮，选择CSV或Excel格式

## 项目结构

```
AMZ搜索词分析系统/
├── src/                    # 源代码
│   ├── app.py              # Streamlit主应用
│   ├── config/             # 配置模块
│   │   ├── settings.py     # 应用设置
│   │   ├── logger.py       # 日志配置
│   │   └── manager.py      # 配置版本管理
│   ├── data/               # 数据处理
│   │   ├── db.py           # 数据库操作
│   │   ├── parser.py       # 文件解析器
│   │   └── aggregator.py   # 数据聚合器
│   ├── rules/              # 规则引擎
│   │   ├── engine.py       # 规则引擎核心
│   │   ├── keyword_rules.py # 关键词规则
│   │   └── asin_rules.py   # ASIN规则
│   ├── ai/                 # AI模块
│   │   ├── client.py       # Gemini客户端
│   │   ├── analyzer.py     # AI分析器
│   │   └── chat.py         # 对话助手
│   ├── export/             # 导出模块
│   │   └── exporter.py     # 报告导出器
│   └── ui/                 # UI组件
│       ├── utils.py        # UI工具函数
│       └── pages/          # 页面
│           ├── home.py     # 首页仪表盘
│           ├── upload.py   # 文件上传
│           ├── analysis.py # 搜索词分析
│           ├── actions.py  # 操作清单
│           └── settings.py # 系统设置
├── tests/                  # 测试
│   ├── unit/               # 单元测试
│   └── integration/        # 集成测试
├── data/                   # 数据目录
│   ├── db/                 # SQLite数据库
│   └── uploads/            # 上传文件临时目录
├── docs/                   # 文档
│   ├── PRD.md              # 产品需求文档
│   ├── Design.md           # 技术设计文档
│   ├── Plan.md             # 开发计划
│   ├── Task.md             # 任务清单
│   └── ADR/                # 架构决策文档
├── .env.example            # 环境变量示例
├── requirements.txt        # Python依赖
├── CHANGELOG.md            # 变更日志
└── README.md               # 本文档
```

## 配置说明

### 环境变量 (.env)

```env
# Gemini API配置
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.5-flash

# 数据库配置（可选）
DB_PATH=data/db/amz_analysis.db

# 日志级别（可选）
LOG_LEVEL=INFO
```

### 规则阈值

在 **系统设置** → **规则配置** 中可调整：

| 阈值 | 默认值 | 说明 |
|-----|-------|------|
| 高花费阈值 | $10 | 花费超过此值且零转化则建议否定 |
| 高ACOS阈值 | 50% | ACOS超过此值建议否定或降低出价 |
| 最小点击数 | 10 | 点击数需达到此值才进行分析 |
| 目标ACOS | 25% | 低于此值视为表现良好 |
| 最小订单数 | 2 | 订单数达到此值才建议手动投放 |

## 常见问题

### Q: 如何获取Gemini API Key？
A: 访问 [Google AI Studio](https://makersuite.google.com/app/apikey)，登录Google账号后创建API Key。

### Q: 支持哪些文件格式？
A: 支持CSV和Excel（.xlsx, .xls）格式。系统自动识别中英文列名。

### Q: 数据存储在哪里？
A: 所有数据存储在本地SQLite数据库（`data/db/amz_analysis.db`），不会上传到云端。

### Q: 如何处理大文件？
A: 系统支持处理1万行以内的数据。对于更大的文件，建议按广告活动拆分后分批上传。

### Q: AI分析不可用怎么办？
A: 检查.env文件中的GEMINI_API_KEY是否正确配置。如果API临时不可用，可以先使用规则分析，之后再进行AI确认。

### Q: 如何回滚错误的配置？
A: 在 **系统设置** → **规则配置** → **配置版本历史** 中，点击 "回滚到此版本"。

## 开发信息

### 技术栈
- **前端**: Streamlit
- **后端**: Python 3.14
- **数据库**: SQLite
- **AI服务**: Google Gemini (google-genai SDK)
- **数据处理**: Pandas, OpenPyXL

### 测试
- 单元测试: pytest
- 测试覆盖: pytest-cov
- 共90+测试用例

### 版本控制
- 遵循 [语义化版本](https://semver.org/lang/zh-CN/)
- 变更记录见 [CHANGELOG.md](CHANGELOG.md)

## 许可证

本项目仅供学习和个人使用。

---

如有问题或建议，欢迎提Issue或联系开发者。
