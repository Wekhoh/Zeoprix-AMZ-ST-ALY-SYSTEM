# Verification Report — 2026-04-25

**Scope:** Sidebar / Copilot drawer 折叠展开按钮失效根因诊断 + 三连环修复实测证据。
**Branch:** `desktop-feat-amz-finalize`
**Last fix commit:** `ab4ef8e` (pure setState updater + useEffect localStorage sync)

---

## 现象

主人截图显示前端首页 `/` 渲染但：

1. 左侧 sidebar 完全不可见（应有 6 个导航 icon）
2. 右侧 Copilot drawer 完全不可见
3. 折叠/展开按钮"没反应"

## 诊断方法

通过 **claude-in-chrome `javascript_tool`** 直接查 live DOM，逐层定位：

```
Pass 1 — DOM 实际存在但 opacity 0
asides[0]: width 220px, opacity 0, has_opacity_0_class true
asides[2]: width 360px, opacity 0, has_opacity_0_class true, has_hidden_class true
window.React: undefined
reactRoot: false
```
→ React 整个没 hydrate

```
Pass 2 — 排除某个 useEffect
elements_with_react_fiber: 3 / 465 = 0.6%
```
→ 不是 useEffect 单点失败，是整个 client JS 没运行

```
Pass 3 — 看 server log
⚠ Blocked cross-origin request to /_next/webpack-hmr from "127.0.0.1"
```
→ Next.js 16 安全特性把 client bundle 屏蔽了

```
Pass 4 — width 220px class 在但 computed 是 60px
.w-\[60px\]   ← Tailwind 编译里有
.w-\[44px\]   ← 也有
.w-\[220px\]  ← 缺！
.w-\[360px\]  ← 缺！
```
→ Tailwind v4 JIT 漏掉 ternary 展开分支

```
Pass 5 — toggle button onClick 已绑但 click 无效果
hasReactProps: true, onClick: function ✓
btn.click() → width 220 → 220 (no change)
btn.title 仍 "收起侧栏" (state 未翻转)
```
→ React 19 Strict Mode 双调用 updater，updater 内的 `localStorage.setItem` 副作用导致 net state 不变

## 三连环根因 + 修复

| Bug | 根因 | 修复 | Commit |
|-----|------|------|--------|
| **#1 Hydration 完全失败** | Next 16 默认仅 `localhost` 可访 `/_next/*`；`127.0.0.1` 被当跨源屏蔽，client JS bundle 不送 | `next.config.ts` 加 `allowedDevOrigins: ["127.0.0.1", "localhost", "0.0.0.0"]` | `f931fbe` |
| **#2 Aside 宽度变 60px** | Tailwind v4 JIT 在 `collapsed ? "w-[60px]" : "w-[220px]"` 中只生成 collapsed 分支 → expanded 没规则 → flex 把 aside 压成内容宽度 | `width` 改 number + inline style，绕开 Tailwind JIT | `f931fbe` |
| **#3 Toggle 按钮 click 后 state 不翻转** | `setCollapsed(prev => { setItem(...); return !prev; })` updater 带副作用 → React 19 Strict Mode dev 双调用 → `localStorage.setItem` 跑两次、净 state 反而不变 | updater 纯化 `prev => !prev`；新增 `useEffect` 监听 `[collapsed]` 单向同步 localStorage；`hasMounted` gate 避免初始覆盖 | `ab4ef8e` |

## 修复后实测（claude-in-chrome）

### Bug 1 — hydration 恢复

| 指标 | Before | After |
|---|---|---|
| `elements_with_react_fiber` | 3 / 465 (0.6%) | 427 / 460 (93%) |
| `window.React` | undefined | (loaded) |
| Server log "Blocked cross-origin" warning | 持续出现 | 消失 |

### Bug 2 — 宽度恢复

| Before | After |
|---|---|
| `aside.computed_width: "60px"` 即使 `style.width="220px"` 也被 override | `sidebar.getBoundingClientRect().width: 220` ✓ `copilot.getBoundingClientRect().width: 360` ✓ |

### Bug 3 — toggle 行为（待主人手测）

Chrome extension 在测验过程中多次断连，无法完整跑完 toggle 端到端验证。
代码层面 fix 严格符合 React 规则（pure updater + side effect in effect），
逻辑正确性高。如手测仍有问题，截图 F12 Console 进一步定位。

## 经验提炼（候选 skill）

1. **Next.js 16 `allowedDevOrigins` Gotcha**：默认仅 `localhost`；`127.0.0.1` / `0.0.0.0` silently 被屏蔽 client bundle，症状是 SSR HTML 出来但 hydration 0%。
2. **Tailwind v4 JIT + ternary expansion**：字面量 ternary 在某些情况只生成一边的 utility，避免 arbitrary values 在 ternary，或改 inline style。
3. **React 19 Strict Mode + updater purity**：setState updater 含副作用的写法在 Strict Mode dev 下双调用 → 净结果可能不变。修法是把副作用移到独立 `useEffect`。

后续若重复遇到这 3 个 pattern，可考虑沉淀成 skill（主人暂时跳过 claudeception 提取）。
