# Contributing to AMZ 搜索词分析系统

欢迎贡献。本文档覆盖本地开发环境搭建、提交规范、PR 流程。

## 1 · 环境前置

| 工具 | 要求 | 安装提示 |
|---|---|---|
| Python | 3.11+（推荐 3.11.13） | `winget install Python.Python.3.11` 或从 python.org |
| Node.js | 20.x（与 CI 一致） | `winget install OpenJS.NodeJS.LTS` |
| Git | 2.40+ | `winget install Git.Git` |
| OS | Windows 10/11、macOS 13+、Linux | 主要在 Windows + WSL bash 验证 |

**Windows 注意**：本项目大量脚本使用 `python` 命令。请确保 `python` 解析到 Python 3.11 而非 Microsoft Store stub 或 hermes venv。
推荐显式路径：`C:/Users/<you>/AppData/Local/Programs/Python/Python311/python.exe`。

## 2 · 一次性设置

```bash
# 1. 克隆
git clone <repo-url>
cd AMZ搜索词分析系统

# 2. Python 虚拟环境（推荐）
python -m venv .venv
source .venv/Scripts/activate  # Windows bash
# 或 source .venv/bin/activate  # macOS / Linux
pip install --upgrade pip
pip install -r requirements.txt

# 3. 前端依赖
cd frontend
npm install
cd ..

# 4. 配置 GEMINI_API_KEY
cp .env.example .env  # 若有
# 编辑 .env 写入 GEMINI_API_KEY=...
```

## 3 · 启动开发环境

最方便：

```powershell
# Windows PowerShell
.\start.ps1
```

`start.ps1` 会同时启动后端 (8008) + 前端 (3031) 并打开浏览器。详细参数见脚本内注释。

手动启动（双终端）：

```bash
# 终端 1 — 后端
PYTHONPATH=. DEBUG=true python -m uvicorn src.backend.app:create_app --factory \
    --host 127.0.0.1 --port 8008

# 终端 2 — 前端
cd frontend && npm run dev
```

## 4 · 测试 + 验证

```bash
# 后端 pytest（含 coverage）
DEBUG=true python -m pytest -q --cov=src --cov-report=term

# 前端 TypeScript 严格检查
cd frontend && npx tsc --noEmit

# 前端生产构建
cd frontend && npm run build

# 前端开发服务器（热更新）
cd frontend && npm run dev
```

CI 中执行的命令见 `.github/workflows/ci.yml`。

## 5 · 提交规范（Conventional Commits）

格式：`<type>[scope]: <description>`

常用 type：
- `feat` 新功能
- `fix` Bug 修复
- `refactor` 重构（不改变功能）
- `docs` 仅文档
- `test` 仅测试
- `chore` 构建 / 工具 / 依赖
- `perf` 性能
- `style` 代码风格

示例：
```
feat(backend): add /metrics endpoint for HTTP timing observability
fix(frontend): copilot panel signal non-null assertion
docs: changelog for Sprint 5
```

**单次提交只做一件事**。本仓库 history 上偶有 formatter reflow 大量代码也混进 feat commit 的反例（见 ENGINEERING_BACKLOG.md），新提交请避免。

## 6 · 分支约定

- `main` / `master` — 主分支（保护，仅 PR 合入）
- `feat/<topic>` — 新功能分支
- `fix/<topic>` — Bug 修复分支
- `refactor/<topic>` — 重构分支
- `docs/<topic>` — 文档分支

## 7 · Pull Request 流程

1. 从 `main` 切出新分支
2. 完成改动 + 跑通 `pytest` + `npm run build`
3. 提交并推送到远端
4. 在 GitHub 开 PR，标题用 Conventional Commits 格式
5. PR 描述模板：

   ```markdown
   ## Summary
   <1-3 bullet points>

   ## Test Plan
   - [ ] pytest passes
   - [ ] npm run build passes
   - [ ] manual chrome verification on /
   ```

6. CI 全绿 + 至少 1 review approve 后合入

## 8 · 工程债务跟踪

进行中的重构 / 工程化项目记录在 [`docs/ENGINEERING_BACKLOG.md`](docs/ENGINEERING_BACKLOG.md)。
建议挑选 🟢 quick win 项作为新人首次贡献入口。

## 9 · 反 AI-Slop 约定

- ❌ 不要在一个 commit 里做"顺手 reformat 整文件"。请只改 task 涉及的行。
- ❌ 不要为不存在的需求增加配置项 / 抽象层 / 可选参数。
- ❌ 不要写"过度防御"的 try/except 包裹不可能失败的代码。
- ✅ 保持小而专的 commit，可读 git blame 是项目的核心债务防线。

更多代码风格见 `~/.claude/rules/coding-style.md`（如适用）和现有代码模式。
