"""
AMZ搜索词分析系统 - 统一样式定义
设计风格: 现代SaaS风 (Notion/Linear风格)
主色调: 深蓝色系
"""

# 全局CSS样式 - 设计系统
GLOBAL_CSS = """
<style>
/* ═══════════════════════════════════════════════════════════════
   AMZ搜索词分析系统 - 设计系统
   风格: 现代SaaS (Notion/Linear风格)
   主色调: 深蓝色系
   ═══════════════════════════════════════════════════════════════ */

/* ═══════════════════════════════════════════════════════════════
   Premium Typography System
   Display: Plus Jakarta Sans (现代几何感)
   Body: DM Sans (优雅易读)
   Mono: JetBrains Mono (技术数据)
   ═══════════════════════════════════════════════════════════════ */
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=DM+Sans:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
    /* ===== 背景层次 ===== */
    --bg-base: #FAFBFC;
    --bg-surface: #FFFFFF;
    --bg-elevated: #F4F5F7;
    --bg-sidebar: #F8FAFC;
    --bg-input: #F1F5F9;

    /* ===== 深蓝色系 ===== */
    --primary-900: #0F172A;
    --primary-800: #1E293B;
    --primary-700: #334155;
    --primary-600: #475569;
    --primary-500: #64748B;
    --primary-400: #94A3B8;
    --primary-300: #CBD5E1;
    --primary-200: #E2E8F0;
    --primary-100: #F1F5F9;

    /* ===== 强调色 - 品牌蓝 ===== */
    --accent: #2563EB;
    --accent-hover: #1D4ED8;
    --accent-light: #DBEAFE;
    --accent-lighter: #EFF6FF;

    /* ===== 语义色 ===== */
    --success: #10B981;
    --success-light: #D1FAE5;
    --warning: #F59E0B;
    --warning-light: #FEF3C7;
    --danger: #EF4444;
    --danger-light: #FEE2E2;
    --info: #3B82F6;
    --info-light: #DBEAFE;

    /* ===== 文字色 ===== */
    --text-primary: #1E293B;
    --text-secondary: #64748B;
    --text-muted: #94A3B8;
    --text-inverse: #FFFFFF;

    /* ===== 边框 ===== */
    --border-subtle: #E2E8F0;
    --border-default: #CBD5E1;
    --border-strong: #94A3B8;

    /* ===== 阴影 ===== */
    --shadow-sm: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
    --shadow-card: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.08);
    --shadow-md: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -2px rgba(0, 0, 0, 0.1);
    --shadow-lg: 0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -4px rgba(0, 0, 0, 0.1);

    /* ===== 圆角 ===== */
    --radius-sm: 6px;
    --radius-md: 10px;
    --radius-lg: 14px;
    --radius-xl: 18px;
    --radius-full: 9999px;

    /* ===== 间距 ===== */
    --space-xs: 0.25rem;
    --space-sm: 0.5rem;
    --space-md: 1rem;
    --space-lg: 1.5rem;
    --space-xl: 2rem;
    --space-2xl: 3rem;

    /* ===== 字体系统 - Premium Typography ===== */
    --font-display: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    --font-sans: 'DM Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    --font-mono: 'JetBrains Mono', 'SF Mono', 'Monaco', monospace;

    /* ===== 高级背景纹理 ===== */
    --noise-texture: url("data:image/svg+xml,%3Csvg viewBox='0 0 200 200' xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='noise'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.65' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23noise)' opacity='0.03'/%3E%3C/svg%3E");
    --grid-pattern: linear-gradient(rgba(37, 99, 235, 0.03) 1px, transparent 1px),
                    linear-gradient(90deg, rgba(37, 99, 235, 0.03) 1px, transparent 1px);
    --mesh-gradient: radial-gradient(at 40% 20%, rgba(37, 99, 235, 0.08) 0px, transparent 50%),
                     radial-gradient(at 80% 80%, rgba(16, 185, 129, 0.06) 0px, transparent 50%),
                     radial-gradient(at 10% 90%, rgba(139, 92, 246, 0.05) 0px, transparent 50%);

    /* ===== 过渡 ===== */
    --transition-fast: 150ms ease;
    --transition-base: 200ms ease;
    --transition-slow: 300ms ease;
}

/* ===== 全局基础 ===== */
.stApp {
    background: var(--bg-base) !important;
    min-height: 100vh !important;
    height: auto !important;
    overflow: visible !important;
}

/* 微妙的噪点纹理叠加 - 注意：已禁用以避免覆盖问题 */
/* 如需启用噪点纹理，取消下面的注释
.stApp::before {
    content: '';
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-image: var(--noise-texture);
    pointer-events: none;
    z-index: -1;
    opacity: 0.3;
}
*/

html, body, [class*="css"] {
    font-family: var(--font-sans) !important;
    -webkit-font-smoothing: antialiased;
    -moz-osx-font-smoothing: grayscale;
    text-rendering: optimizeLegibility;
}

/* 隐藏默认元素 */
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header[data-testid="stHeader"] {background: transparent;}

/* 主内容区 */
.main .block-container {
    padding-top: 1.75rem;
    padding-bottom: var(--space-xl);
    padding-left: 2.25rem;
    padding-right: 2.25rem;
    max-width: 1280px;
}

/* ===== 标题样式 - Premium Typography ===== */
h1 {
    font-family: var(--font-display) !important;
    font-size: 2rem !important;
    font-weight: 800 !important;
    color: var(--primary-900) !important;
    letter-spacing: -0.03em !important;
    margin-bottom: var(--space-lg) !important;
}

h2 {
    font-family: var(--font-display) !important;
    font-size: 1.5rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    letter-spacing: -0.02em !important;
}

h3 {
    font-family: var(--font-display) !important;
    font-size: 1.25rem !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
}

/* ===== 侧边栏 - 增强版 ===== */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #F8FAFC 0%, #F5F7FB 48%, #EEF3FA 100%) !important;
    border-right: 1px solid var(--border-subtle);
    position: relative;
    z-index: 30 !important;
    isolation: isolate;
}

/* 侧边栏顶部装饰渐变 */
[data-testid="stSidebar"] > div:first-child::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 120px;
    background: linear-gradient(180deg, rgba(37, 99, 235, 0.06) 0%, transparent 100%);
    pointer-events: none;
    z-index: 0;
}

/* 注意: 左边缘的粉红色装饰条来自Streamlit框架核心渲染层，
   无法通过CSS/JS覆盖。这是一个已知的框架限制。 */

/* 隐藏Streamlit默认的左侧装饰条 - 多重覆盖策略 */
[data-testid="stSidebar"]::before,
[data-testid="stSidebarContent"]::before,
[data-testid="stSidebarNav"]::before,
section[data-testid="stSidebar"] > div::before,
.stApp > div::before,
[data-testid="stAppViewContainer"]::before {
    display: none !important;
    content: none !important;
    background: transparent !important;
}

/* 覆盖可能的边框装饰颜色 */
[data-testid="stSidebar"],
[data-testid="stSidebar"] > div,
[data-testid="stSidebar"] section,
.stApp,
[data-testid="stAppViewContainer"] {
    border-left: none !important;
    box-shadow: none !important;
}

/* 确保sidebar内容区域背景与覆盖层一致 */
[data-testid="stSidebar"] > div:first-child::before {
    background: transparent !important;
    display: none !important;
}

[data-testid="stSidebar"] > div:first-child {
    background: transparent !important;
    padding: 1.25rem 0.875rem 1rem 0.875rem;
    position: relative;
    z-index: 1;
}

/* 强制覆盖Streamlit主题色变量 */
.stApp [class*="st-emotion-cache"] {
    --primary-color: #2563EB !important;
}

/* 侧边栏品牌区 */
.sidebar-brand-shell {
    padding: 0.25rem 0 0.5rem 0;
}

.sidebar-eyebrow {
    display: inline-flex;
    align-items: center;
    gap: 0.35rem;
    padding: 0.28rem 0.6rem;
    border-radius: 999px;
    background: rgba(37, 99, 235, 0.08);
    color: var(--accent);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.sidebar-brand-shell h1 {
    font-size: 1.5rem !important;
    color: var(--primary-900) !important;
    font-weight: 800 !important;
    margin: 0.9rem 0 0.35rem 0 !important;
    padding-bottom: 0 !important;
    border-bottom: none !important;
}

.sidebar-brand-shell p {
    margin: 0;
    color: var(--text-secondary);
    font-size: 0.88rem;
    line-height: 1.55;
}

.sidebar-section-label {
    font-size: 0.72rem;
    font-weight: 700;
    color: var(--text-muted);
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 0 0 0.55rem 0;
}

.sidebar-current-product {
    margin-top: 0.7rem;
    padding: 0.85rem 0.95rem;
    border-radius: 14px;
    border: 1px solid rgba(148, 163, 184, 0.2);
    background: rgba(255, 255, 255, 0.72);
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.sidebar-current-product span {
    display: block;
    color: var(--text-muted);
    font-size: 0.72rem;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.35rem;
}

.sidebar-current-product strong {
    display: block;
    color: var(--primary-900);
    font-size: 0.95rem;
    font-weight: 700;
}

[data-testid="stSidebar"] .stRadio > label {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: var(--space-sm) !important;
}

[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
    padding: 0.72rem 0.9rem !important;
    border-radius: 14px !important;
    margin: 0.18rem 0 !important;
    transition: all var(--transition-fast) !important;
    border: 1px solid transparent !important;
    background: transparent !important;
}

[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:hover {
    background: var(--primary-100) !important;
    border-color: var(--border-subtle) !important;
}

/* 修复Radio按钮选中状态 - 高对比度版本 */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-checked="true"],
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label[data-baseweb="radio"]:has(input:checked),
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] + div label[data-checked="true"] {
    background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
    color: white !important;
    font-weight: 600 !important;
    border-color: var(--accent-hover) !important;
    box-shadow: 0 8px 18px rgba(37, 99, 235, 0.18) !important;
}

/* 选中状态内部文字强制白色 + 透明背景 */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) p,
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) span,
[data-testid="stSidebar"] .stRadio label:has(input[type="radio"]:checked) p,
[data-testid="stSidebar"] .stRadio label:has(input[type="radio"]:checked) [data-testid="stMarkdownContainer"] p,
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) p,
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) [data-testid="stMarkdownContainer"] p {
    color: white !important;
}

/* 选中状态文字容器背景透明 - 关键修复 */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label:has(input:checked) > div:last-child,
[data-testid="stSidebar"] .stRadio label:has(input[type="radio"]:checked) > div:not(:first-child),
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) > div:last-of-type,
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) [data-testid="stMarkdownContainer"] {
    background: transparent !important;
    background-color: transparent !important;
}

/* Radio圆点 - 选中状态用白色填充（在蓝色背景上） */
[data-testid="stSidebar"] .stRadio input[type="radio"]:checked + div,
[data-testid="stSidebar"] .stRadio label:has(input[type="radio"]:checked) > div:first-child,
[data-testid="stSidebar"] label input[type="radio"]:checked ~ div,
[data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) > div:first-of-type {
    background-color: white !important;
    border-color: white !important;
}

/* Radio选中时的内部点 - 深蓝色 */
[data-testid="stSidebar"] .stRadio input[type="radio"]:checked + div::after,
[data-testid="stSidebar"] label:has(input[type="radio"]:checked) > div:first-child::after {
    background-color: var(--accent-hover) !important;
}

/* Radio圆点外圈 - 未选中状态 */
[data-testid="stSidebar"] .stRadio input[type="radio"] + div,
[data-testid="stSidebar"] [role="radiogroup"] label:not(:has(input:checked)) > div:first-of-type {
    border-color: var(--border-default) !important;
    background-color: transparent !important;
}

[data-testid="stSidebar"] .stRadio input[type="radio"]:hover + div,
[data-testid="stSidebar"] label:hover input[type="radio"] ~ div:first-of-type {
    border-color: var(--accent) !important;
}

/* 强制覆盖Streamlit的主题色 - 全局CSS变量 */
:root {
    --primary-color: #2563EB !important;
}

/* 针对Streamlit动态类的通用覆盖 */
[data-testid="stSidebar"] label[data-baseweb="radio"] > div[class*="st-"]:first-child,
[data-testid="stSidebar"] div[role="radiogroup"] label > div:first-child {
    background-color: transparent !important;
}

[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) > div[class*="st-"]:first-child,
[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) > div:first-child {
    background-color: var(--accent) !important;
}

/* ===== 按钮 ===== */
.stButton > button {
    font-family: var(--font-sans) !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    padding: 0.75rem 1.5rem !important;
    border-radius: var(--radius-md) !important;
    transition: all var(--transition-fast) !important;
    border: 1px solid transparent !important;
    letter-spacing: 0.01em;
}

/* 主要按钮 - 使用渐变背景 */
.stButton > button[kind="primary"],
.stButton > button:not([kind]):not([data-testid]) {
    background: linear-gradient(135deg, var(--accent) 0%, var(--accent-hover) 100%) !important;
    color: var(--text-inverse) !important;
    border-color: var(--accent) !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25) !important;
}

.stButton > button[kind="primary"]:hover,
.stButton > button:not([kind]):not([data-testid]):hover {
    background: linear-gradient(135deg, var(--accent-hover) 0%, #1E40AF 100%) !important;
    border-color: var(--accent-hover) !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.35) !important;
    transform: translateY(-2px);
}

/* 次要按钮/轮廓按钮 - 快速操作使用 - 增强版 */
.stButton > button[kind="secondary"],
.main .stButton > button {
    background: linear-gradient(135deg, var(--bg-surface) 0%, #F8FAFC 100%) !important;
    color: var(--text-primary) !important;
    border: 1px solid var(--border-subtle) !important;
    box-shadow: var(--shadow-card), inset 0 1px 0 rgba(255,255,255,0.8) !important;
    position: relative !important;
    overflow: hidden !important;
    padding-left: 1.75rem !important;
}

/* 按钮左侧装饰线 */
.main .stButton > button::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 4px;
    background: linear-gradient(180deg, var(--accent) 0%, #3B82F6 50%, #60A5FA 100%);
    opacity: 0.8;
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* 按钮悬浮时装饰线变亮 */
.main .stButton > button:hover::before {
    width: 5px;
    opacity: 1;
    box-shadow: 2px 0 8px rgba(37, 99, 235, 0.3);
}

/* 按钮背景光晕效果 */
.main .stButton > button::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 20%;
    width: 60%;
    height: 100%;
    background: radial-gradient(ellipse at center, rgba(37, 99, 235, 0.08) 0%, transparent 70%);
    transform: translateY(-50%);
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
}

.main .stButton > button:hover::after {
    opacity: 1;
}

.stButton > button[kind="secondary"]:hover,
.main .stButton > button:hover {
    background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%) !important;
    border-color: var(--accent-light) !important;
    color: var(--accent) !important;
    box-shadow: 0 4px 16px rgba(37, 99, 235, 0.15),
                0 2px 4px rgba(0, 0, 0, 0.05),
                inset 0 1px 0 rgba(255,255,255,0.9) !important;
    transform: translateY(-2px);
}

/* 悬浮时的图标效果 */
.stButton > button:active {
    transform: translateY(0) !important;
    box-shadow: var(--shadow-sm) !important;
}

/* 禁用状态 */
.stButton > button:disabled {
    opacity: 0.5 !important;
    cursor: not-allowed !important;
    transform: none !important;
}

/* ===== 指标卡片 (st.metric) - Glassmorphism Premium ===== */
[data-testid="stMetric"] {
    background: linear-gradient(145deg,
        rgba(255, 255, 255, 0.95) 0%,
        rgba(248, 250, 252, 0.9) 50%,
        rgba(241, 245, 249, 0.85) 100%) !important;
    border: 1px solid rgba(255, 255, 255, 0.8) !important;
    border-radius: var(--radius-xl) !important;
    padding: var(--space-lg) var(--space-xl) !important;
    box-shadow:
        0 4px 24px -4px rgba(0, 0, 0, 0.08),
        0 1px 2px rgba(0, 0, 0, 0.04),
        inset 0 1px 0 rgba(255, 255, 255, 1),
        inset 0 -1px 0 rgba(0, 0, 0, 0.02) !important;
    transition: all 0.4s cubic-bezier(0.22, 1, 0.36, 1) !important;
    position: relative;
    overflow: hidden;
    backdrop-filter: blur(20px) saturate(180%);
    -webkit-backdrop-filter: blur(20px) saturate(180%);
}

/* 卡片顶部彩色强调条 - 始终显示 */
[data-testid="stMetric"]::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, var(--accent) 0%, #60A5FA 100%);
    opacity: 1;
    transition: height 0.3s ease;
}

/* 第1个卡片 - 蓝色 (总花费) */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) [data-testid="stMetric"]::before {
    background: linear-gradient(90deg, #2563EB 0%, #3B82F6 50%, #60A5FA 100%) !important;
}

/* 第2个卡片 - 绿色 (总订单) */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"]::before {
    background: linear-gradient(90deg, #059669 0%, #10B981 50%, #34D399 100%) !important;
}

/* 第3个卡片 - 琥珀色 (ACOS) */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"]::before {
    background: linear-gradient(90deg, #D97706 0%, #F59E0B 50%, #FBBF24 100%) !important;
}

/* 第4个卡片 - 紫色 (搜索词数) */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"]::before {
    background: linear-gradient(90deg, #7C3AED 0%, #8B5CF6 50%, #A78BFA 100%) !important;
}

/* 卡片悬浮效果 - Premium Elevation */
[data-testid="stMetric"]:hover {
    box-shadow:
        0 20px 40px -12px rgba(37, 99, 235, 0.25),
        0 8px 16px -4px rgba(0, 0, 0, 0.1),
        inset 0 1px 0 rgba(255, 255, 255, 1) !important;
    border-color: rgba(37, 99, 235, 0.2) !important;
    transform: translateY(-6px) scale(1.02);
}

[data-testid="stMetric"]:hover::before {
    height: 5px;
    filter: brightness(1.1);
}

[data-testid="stMetricLabel"] {
    font-family: var(--font-display) !important;
    font-size: 0.7rem !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.375rem !important;
}

[data-testid="stMetricValue"] {
    font-family: var(--font-mono) !important;
    font-size: 2.25rem !important;
    font-weight: 700 !important;
    color: var(--text-primary) !important;
    line-height: 1.1;
    background: linear-gradient(135deg, var(--primary-900) 0%, var(--accent) 60%, #60A5FA 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    transition: all 0.3s ease;
}

/* 指标变化值 */
[data-testid="stMetricDelta"] {
    font-size: 0.8125rem !important;
    font-weight: 600 !important;
}

/* ===== 表格 ===== */
[data-testid="stDataFrame"],
.stDataFrame {
    background: var(--bg-surface) !important;
    border-radius: var(--radius-lg) !important;
    border: 1px solid var(--border-subtle) !important;
    box-shadow: var(--shadow-sm) !important;
    overflow: hidden;
}

[data-testid="stDataFrame"] th {
    background: var(--bg-elevated) !important;
    font-weight: 600 !important;
    color: var(--text-secondary) !important;
    text-transform: uppercase;
    font-size: 0.75rem !important;
    letter-spacing: 0.05em;
    padding: var(--space-md) !important;
    border-bottom: 1px solid var(--border-subtle) !important;
}

[data-testid="stDataFrame"] td {
    background: var(--bg-surface) !important;
    color: var(--text-primary) !important;
    padding: var(--space-md) !important;
    border-bottom: 1px solid var(--border-subtle) !important;
    font-size: 0.875rem !important;
}

[data-testid="stDataFrame"] tr:hover td {
    background: var(--primary-100) !important;
}

/* ===== Tab导航 ===== */
.stTabs [data-baseweb="tab-list"] {
    gap: 0;
    background: transparent;
    border-bottom: 1px solid var(--border-subtle);
    padding: 0;
}

.stTabs [data-baseweb="tab"] {
    height: 48px;
    padding: 0 var(--space-lg);
    background: transparent;
    border-radius: 0;
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--text-secondary);
    border-bottom: 2px solid transparent;
    margin-bottom: -1px;
    transition: all var(--transition-fast);
}

.stTabs [data-baseweb="tab"]:hover {
    color: var(--text-primary);
    background: var(--bg-elevated);
}

/* Tab选中状态 - 多种选择器确保覆盖 */
.stTabs [aria-selected="true"],
.stTabs [data-baseweb="tab"][aria-selected="true"],
.stTabs button[aria-selected="true"] {
    color: var(--accent) !important;
    border-bottom-color: var(--accent) !important;
    font-weight: 600 !important;
    background: transparent !important;
}

/* Tab高亮指示器 - 覆盖默认红色 */
.stTabs [data-baseweb="tab-highlight"],
.stTabs div[data-baseweb="tab-highlight"] {
    background-color: var(--accent) !important;
}

/* Tab border指示器 */
.stTabs [data-baseweb="tab-border"] {
    background-color: var(--border-subtle) !important;
}

/* ===== 输入框 ===== */
.stTextInput > div > div > input,
.stTextArea textarea,
.stNumberInput > div > div > input {
    background: var(--bg-input) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    font-size: 0.875rem !important;
    padding: 0.75rem 1rem !important;
    color: var(--text-primary) !important;
    transition: all var(--transition-fast) !important;
}

.stTextInput > div > div > input:focus,
.stTextArea textarea:focus,
.stNumberInput > div > div > input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-lighter) !important;
    background: var(--bg-surface) !important;
}

.stTextInput > div > div > input::placeholder,
.stTextArea textarea::placeholder {
    color: var(--text-muted) !important;
}

/* ===== 选择框 ===== */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    background: var(--bg-input) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
}

.stSelectbox > div > div:focus-within,
.stMultiSelect > div > div:focus-within {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px var(--accent-lighter) !important;
}

/* ===== 消息提示 - 增强版 ===== */
/* 通用Alert样式 */
.stAlert,
[data-testid="stAlert"],
.element-container:has(.stAlert) .stAlert {
    border-radius: var(--radius-lg) !important;
    border-left-width: 5px !important;
    padding: var(--space-lg) var(--space-xl) !important;
    margin: var(--space-md) 0 !important;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04), 0 1px 2px rgba(0, 0, 0, 0.06) !important;
    transition: all 0.2s ease !important;
    position: relative;
    overflow: hidden;
}

.stAlert:hover,
[data-testid="stAlert"]:hover {
    transform: translateX(2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06), 0 2px 4px rgba(0, 0, 0, 0.08) !important;
}

/* Success消息 - 绿色系 */
[data-testid="stAlert"][data-baseweb-alert-kind="positive"],
.stSuccess,
[data-testid="stNotification"][kind="success"],
div[data-stale="false"] > div > div > .stAlert:has([data-testid="stMarkdownContainer"]) {
    background: linear-gradient(135deg, #ECFDF5 0%, #D1FAE5 50%, #A7F3D0 100%) !important;
    border-left-color: #059669 !important;
    border: 1px solid #6EE7B7 !important;
    border-left-width: 5px !important;
}

[data-testid="stAlert"][data-baseweb-alert-kind="positive"]::before,
.stSuccess::before {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 80px;
    height: 100%;
    background: radial-gradient(circle at 100% 50%, rgba(16, 185, 129, 0.1) 0%, transparent 70%);
    pointer-events: none;
}

/* Warning消息 - 琥珀色系 */
[data-testid="stAlert"][data-baseweb-alert-kind="warning"],
.stWarning {
    background: linear-gradient(135deg, #FFFBEB 0%, #FEF3C7 50%, #FDE68A 100%) !important;
    border-left-color: #D97706 !important;
    border: 1px solid #FCD34D !important;
    border-left-width: 5px !important;
}

[data-testid="stAlert"][data-baseweb-alert-kind="warning"]::before,
.stWarning::before {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 80px;
    height: 100%;
    background: radial-gradient(circle at 100% 50%, rgba(245, 158, 11, 0.1) 0%, transparent 70%);
    pointer-events: none;
}

/* Info消息 - 蓝色系 */
[data-testid="stAlert"][data-baseweb-alert-kind="info"],
.stInfo {
    background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 50%, #BFDBFE 100%) !important;
    border-left-color: #2563EB !important;
    border: 1px solid #93C5FD !important;
    border-left-width: 5px !important;
}

[data-testid="stAlert"][data-baseweb-alert-kind="info"]::before,
.stInfo::before {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 80px;
    height: 100%;
    background: radial-gradient(circle at 100% 50%, rgba(37, 99, 235, 0.1) 0%, transparent 70%);
    pointer-events: none;
}

/* Error消息 - 红色系 */
[data-testid="stAlert"][data-baseweb-alert-kind="negative"],
.stError {
    background: linear-gradient(135deg, #FEF2F2 0%, #FEE2E2 50%, #FECACA 100%) !important;
    border-left-color: #DC2626 !important;
    border: 1px solid #FCA5A5 !important;
    border-left-width: 5px !important;
}

[data-testid="stAlert"][data-baseweb-alert-kind="negative"]::before,
.stError::before {
    content: '';
    position: absolute;
    top: 0;
    right: 0;
    width: 80px;
    height: 100%;
    background: radial-gradient(circle at 100% 50%, rgba(239, 68, 68, 0.1) 0%, transparent 70%);
    pointer-events: none;
}

/* Alert内文字样式 */
.stAlert p,
[data-testid="stAlert"] p {
    color: var(--text-primary) !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    margin: 0 !important;
    letter-spacing: -0.01em;
}

/* ===== 分割线 ===== */
hr {
    border: none !important;
    border-top: 1px solid var(--border-subtle) !important;
    margin: var(--space-lg) 0 !important;
}

/* ===== Expander ===== */
.streamlit-expanderHeader {
    background: var(--bg-elevated) !important;
    border: 1px solid var(--border-subtle) !important;
    border-radius: var(--radius-md) !important;
    font-weight: 600 !important;
    color: var(--text-primary) !important;
    padding: var(--space-md) var(--space-lg) !important;
}

.streamlit-expanderContent {
    background: var(--bg-surface) !important;
    border: 1px solid var(--border-subtle) !important;
    border-top: none !important;
    border-radius: 0 0 var(--radius-md) var(--radius-md) !important;
    padding: var(--space-lg) !important;
}

/* ===== AI助手 Popover - Clean Unified Design ===== */
div[data-testid="stPopoverBody"] {
    width: 320px !important;
    max-height: 500px !important;
    border-radius: 14px !important;
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12) !important;
    border: 1px solid rgba(0, 0, 0, 0.06) !important;
    background: #ffffff !important;
    padding: 16px !important;
    box-sizing: border-box !important;
    overflow: hidden !important;
}

/* 内部容器 - 清除所有默认间距 */
div[data-testid="stPopoverBody"] > div:first-child {
    padding: 0 !important;
    margin: 0 !important;
    background: transparent !important;
}

div[data-testid="stPopoverBody"] > div > div {
    background: transparent !important;
}

/* AI助手标题 */
div[data-testid="stPopoverBody"] h3 {
    font-size: 0.9375rem !important;
    font-weight: 700 !important;
    color: #1e293b !important;
    margin: 0 0 2px 0 !important;
    padding: 0 !important;
    background: transparent !important;
    letter-spacing: -0.01em !important;
}

/* 副标题 */
div[data-testid="stPopoverBody"] .stCaption,
div[data-testid="stPopoverBody"] p[data-testid="stCaptionContainer"],
div[data-testid="stPopoverBody"] [data-testid="stCaptionContainer"] {
    color: #64748b !important;
    margin: 0 0 12px 0 !important;
    padding: 0 !important;
    font-size: 0.75rem !important;
    background: transparent !important;
    border: none !important;
}

/* 描述文字 */
div[data-testid="stPopoverBody"] p:not([data-testid]) {
    font-size: 0.8125rem !important;
    color: #475569 !important;
    line-height: 1.5 !important;
    margin: 0 0 10px 0 !important;
    padding: 0 !important;
    background: transparent !important;
}

/* 快捷问题标签 */
div[data-testid="stPopoverBody"] strong,
div[data-testid="stPopoverBody"] b {
    font-size: 0.6875rem !important;
    font-weight: 600 !important;
    color: #94a3b8 !important;
    text-transform: uppercase !important;
    letter-spacing: 0.04em !important;
    display: block !important;
    padding: 0 !important;
    margin: 0 0 8px 0 !important;
    background: transparent !important;
}

/* 按钮容器 */
div[data-testid="stPopoverBody"] [data-testid="stHorizontalBlock"] {
    gap: 6px !important;
    padding: 0 !important;
    margin: 0 0 6px 0 !important;
    background: transparent !important;
}

/* 快捷按钮 */
div[data-testid="stPopoverBody"] .stButton > button {
    width: 100% !important;
    justify-content: center !important;
    padding: 9px 10px !important;
    font-size: 0.8125rem !important;
    font-weight: 500 !important;
    margin: 0 !important;
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    color: #334155 !important;
    transition: all 0.15s ease !important;
    box-shadow: none !important;
    min-height: 38px !important;
}

div[data-testid="stPopoverBody"] .stButton > button:hover {
    background: #2563eb !important;
    border-color: #2563eb !important;
    color: #ffffff !important;
    box-shadow: 0 2px 8px rgba(37, 99, 235, 0.2) !important;
}

/* 分割线 */
div[data-testid="stPopoverBody"] hr {
    margin: 12px 0 !important;
    border: none !important;
    height: 1px !important;
    background: #e2e8f0 !important;
}

/* 消息容器 */
div[data-testid="stPopoverBody"] [data-testid="stVerticalBlockBorderWrapper"] {
    margin: 0 !important;
    padding: 0 !important;
    background: transparent !important;
}

div[data-testid="stPopoverBody"] [data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 8px !important;
    background: #f8fafc !important;
    border-radius: 8px !important;
    border: 1px solid #e2e8f0 !important;
    margin: 8px 0 !important;
}

/* 聊天消息 */
div[data-testid="stPopoverBody"] [data-testid="stChatMessage"] {
    background: transparent !important;
    padding: 6px 0 !important;
    gap: 8px !important;
}

div[data-testid="stPopoverBody"] [data-testid="stChatMessage"] [data-testid="stMarkdownContainer"] {
    font-size: 0.8125rem !important;
    line-height: 1.5 !important;
}

/* 聊天输入框 */
div[data-testid="stPopoverBody"] [data-testid="stChatInput"] {
    margin: 8px 0 0 0 !important;
    padding: 0 !important;
    background: transparent !important;
}

div[data-testid="stPopoverBody"] [data-testid="stChatInput"] > div {
    background: #f8fafc !important;
    border: 1px solid #e2e8f0 !important;
    border-radius: 8px !important;
    overflow: hidden !important;
}

div[data-testid="stPopoverBody"] [data-testid="stChatInput"] textarea,
div[data-testid="stPopoverBody"] [data-testid="stChatInput"] input {
    background: transparent !important;
    border: none !important;
    padding: 10px 12px !important;
    font-size: 0.8125rem !important;
    color: #1e293b !important;
}

div[data-testid="stPopoverBody"] [data-testid="stChatInput"] textarea::placeholder,
div[data-testid="stPopoverBody"] [data-testid="stChatInput"] input::placeholder {
    color: #94a3b8 !important;
}

div[data-testid="stPopoverBody"] [data-testid="stChatInput"] button {
    background: #2563eb !important;
    border: none !important;
    border-radius: 6px !important;
    margin: 4px !important;
}

div[data-testid="stPopoverBody"] [data-testid="stChatInput"] button:hover {
    background: #1d4ed8 !important;
}

/* Popover触发按钮 */
button[data-testid="stPopoverButton"] {
    background: #2563eb !important;
    color: white !important;
    border: none !important;
    border-radius: 10px !important;
    padding: 8px 14px !important;
    font-weight: 600 !important;
    font-size: 0.875rem !important;
    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.2) !important;
}

button[data-testid="stPopoverButton"]:hover {
    background: #1d4ed8 !important;
    box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3) !important;
}

/* ===== 文件上传 ===== */
[data-testid="stFileUploader"] {
    background: var(--bg-surface) !important;
    border: 2px dashed var(--border-default) !important;
    border-radius: var(--radius-lg) !important;
    padding: var(--space-xl) !important;
    transition: all var(--transition-fast) !important;
}

[data-testid="stFileUploader"]:hover {
    border-color: var(--accent) !important;
    background: var(--accent-lighter) !important;
}

/* ===== Slider ===== */
.stSlider > div > div > div {
    background: var(--primary-200) !important;
}

.stSlider > div > div > div > div {
    background: var(--accent) !important;
}

/* ===== Checkbox ===== */
.stCheckbox > label > div[data-testid="stMarkdownContainer"] {
    font-size: 0.875rem !important;
    color: var(--text-primary) !important;
}

/* ===== Progress Bar ===== */
.stProgress > div > div > div > div {
    background: var(--accent) !important;
    border-radius: var(--radius-full) !important;
}

/* ===== 图表容器 ===== */
[data-testid="stVegaLiteChart"],
[data-testid="stPlotlyChart"] {
    background: var(--bg-surface) !important;
    border-radius: var(--radius-lg) !important;
    border: 1px solid var(--border-subtle) !important;
    padding: var(--space-md) !important;
}

/* ===== 小标题/Section Headers (h2, subheader) ===== */
.main h2,
.stSubheader {
    font-size: 1.125rem !important;
    font-weight: 700 !important;
    color: var(--primary-800) !important;
    margin-top: var(--space-lg) !important;
    margin-bottom: var(--space-md) !important;
    padding-bottom: var(--space-sm);
    border-bottom: 2px solid var(--primary-100);
    display: inline-block;
    letter-spacing: -0.01em;
}

/* 主标题优化 */
.main h1 {
    font-size: 1.75rem !important;
    font-weight: 700 !important;
    color: var(--primary-900) !important;
    letter-spacing: -0.02em !important;
    margin-bottom: var(--space-xl) !important;
    position: relative;
    padding-left: 0.75rem;
}

.main h1::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0.25rem;
    bottom: 0.25rem;
    width: 4px;
    background: linear-gradient(180deg, var(--accent) 0%, var(--accent-hover) 100%);
    border-radius: var(--radius-full);
}

/* ===== 分割线增强 ===== */
.main hr,
[data-testid="stVerticalBlock"] > hr {
    border: none !important;
    height: 1px !important;
    background: linear-gradient(90deg, transparent 0%, var(--border-subtle) 20%, var(--border-subtle) 80%, transparent 100%) !important;
    margin: var(--space-xl) 0 !important;
}

/* ===== 列布局间距 ===== */
[data-testid="column"] {
    padding: 0 var(--space-sm) !important;
}

[data-testid="column"]:first-child {
    padding-left: 0 !important;
}

[data-testid="column"]:last-child {
    padding-right: 0 !important;
}

/* ===== 下拉选择框增强 ===== */
[data-testid="stSidebar"] .stSelectbox > div > div {
    background: rgba(255, 255, 255, 0.92) !important;
    border: 1px solid rgba(148, 163, 184, 0.26) !important;
    border-radius: 14px !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.05) !important;
}

[data-testid="stSidebar"] .stSelectbox > div > div:hover {
    border-color: var(--accent) !important;
}

/* ===== 产品选择器标签 ===== */
[data-testid="stSidebar"] .stSelectbox > label {
    font-size: 0.75rem !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    text-transform: uppercase !important;
    letter-spacing: 0.05em !important;
    margin-bottom: 0.35rem !important;
}

/* ===== 空状态提示 ===== */
.main .stInfo:only-child {
    text-align: center;
    padding: var(--space-2xl) !important;
    background: linear-gradient(135deg, var(--bg-elevated) 0%, var(--primary-100) 100%) !important;
    border: 1px dashed var(--border-default) !important;
    border-radius: var(--radius-xl) !important;
}

/* ===== 响应式调整 ===== */
@media (max-width: 768px) {
    .main .block-container {
        padding-left: var(--space-md);
        padding-right: var(--space-md);
    }

    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important;
    }
}

/* ═══════════════════════════════════════════════════════════════
   创意增强 - 动画与微交互
   ═══════════════════════════════════════════════════════════════ */

/* ===== 入场动画 ===== */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideInLeft {
    from {
        opacity: 0;
        transform: translateX(-20px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
}

@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

/* 主内容区入场动画 - 已简化避免空白问题 */
.main .block-container > div {
    opacity: 1;
}

/* 指标卡片交错入场 - 简化动画 */
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(1) [data-testid="stMetric"] {
    animation: fadeInUp 0.4s ease-out 0.05s forwards;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(2) [data-testid="stMetric"] {
    animation: fadeInUp 0.4s ease-out 0.1s forwards;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(3) [data-testid="stMetric"] {
    animation: fadeInUp 0.4s ease-out 0.15s forwards;
}
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"]:nth-child(4) [data-testid="stMetric"] {
    animation: fadeInUp 0.4s ease-out 0.2s forwards;
}

/* 侧边栏入场动画 */
[data-testid="stSidebar"] {
    animation: slideInLeft 0.3s ease-out;
}

/* ===== 自定义滚动条 ===== */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-elevated);
    border-radius: var(--radius-full);
}

::-webkit-scrollbar-thumb {
    background: linear-gradient(180deg, var(--primary-300) 0%, var(--primary-400) 100%);
    border-radius: var(--radius-full);
    border: 2px solid var(--bg-elevated);
}

::-webkit-scrollbar-thumb:hover {
    background: linear-gradient(180deg, var(--primary-400) 0%, var(--primary-500) 100%);
}

/* 侧边栏滚动条 */
[data-testid="stSidebar"]::-webkit-scrollbar {
    width: 6px;
}

[data-testid="stSidebar"]::-webkit-scrollbar-thumb {
    background: var(--primary-200);
}

/* ===== 表格增强 - 交替行色与动画 ===== */
[data-testid="stDataFrame"] tbody tr:nth-child(even) td {
    background: var(--bg-elevated) !important;
}

[data-testid="stDataFrame"] tbody tr {
    transition: all var(--transition-fast) !important;
}

[data-testid="stDataFrame"] tbody tr:hover {
    transform: scale(1.005);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

[data-testid="stDataFrame"] tbody tr:hover td {
    background: var(--accent-lighter) !important;
}

/* 表格单元格文字动画 */
[data-testid="stDataFrame"] td {
    position: relative;
}

/* ===== 按钮图标效果 ===== */
.stButton > button {
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    gap: 0.5rem !important;
}

/* 按钮内SVG图标 */
.stButton > button svg {
    width: 1.125rem;
    height: 1.125rem;
    transition: transform var(--transition-fast);
}

.stButton > button:hover svg {
    transform: scale(1.1);
}

/* 下载按钮特殊效果 */
.stDownloadButton > button {
    background: linear-gradient(135deg, var(--success) 0%, #059669 100%) !important;
    color: white !important;
    border: none !important;
}

.stDownloadButton > button:hover {
    background: linear-gradient(135deg, #059669 0%, #047857 100%) !important;
    box-shadow: 0 4px 12px rgba(16, 185, 129, 0.35) !important;
}

/* ===== 链接样式 ===== */
a {
    color: var(--accent) !important;
    text-decoration: none !important;
    transition: all var(--transition-fast) !important;
    position: relative;
}

a:hover {
    color: var(--accent-hover) !important;
}

a::after {
    content: '';
    position: absolute;
    width: 0;
    height: 2px;
    bottom: -2px;
    left: 0;
    background: var(--accent);
    transition: width var(--transition-base);
}

a:hover::after {
    width: 100%;
}

/* ===== 装饰性背景图案 - 已集成到.stApp ===== */
/* 注意：背景渐变已移至.stApp的background-image */

/* ===== Focus 可访问性增强 ===== */
button:focus-visible,
input:focus-visible,
textarea:focus-visible,
select:focus-visible,
[tabindex]:focus-visible {
    outline: 2px solid var(--accent) !important;
    outline-offset: 2px !important;
}

/* ===== 空状态增强 ===== */
.stAlert[data-baseweb-alert-kind="info"]:only-child,
[data-testid="stAlert"]:only-child {
    text-align: center;
    padding: var(--space-2xl) var(--space-xl) !important;
    background: linear-gradient(135deg, var(--bg-surface) 0%, var(--primary-100) 100%) !important;
    border: 2px dashed var(--border-default) !important;
    border-radius: var(--radius-xl) !important;
    position: relative;
    overflow: hidden;
}

.stAlert:only-child::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: conic-gradient(from 0deg, transparent 0deg, var(--accent-light) 60deg, transparent 120deg);
    animation: rotate 8s linear infinite;
    opacity: 0.1;
}

@keyframes rotate {
    from { transform: rotate(0deg); }
    to { transform: rotate(360deg); }
}

/* ===== 卡片悬浮光效 ===== */
[data-testid="stMetric"]::after {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: linear-gradient(135deg, rgba(255,255,255,0) 0%, rgba(255,255,255,0.8) 50%, rgba(255,255,255,0) 100%);
    transform: translateX(-100%) skewX(-15deg);
    transition: transform 0.6s ease;
    pointer-events: none;
}

[data-testid="stMetric"]:hover::after {
    transform: translateX(100%) skewX(-15deg);
}

/* ===== 数字输入框增强 ===== */
.stNumberInput > div > div {
    border-radius: var(--radius-md) !important;
    overflow: hidden;
    box-shadow: var(--shadow-sm) !important;
}

.stNumberInput button {
    background: var(--bg-elevated) !important;
    border: none !important;
    color: var(--text-secondary) !important;
    transition: all var(--transition-fast) !important;
}

.stNumberInput button:hover {
    background: var(--accent-light) !important;
    color: var(--accent) !important;
}

/* ===== Tab 下划线动画 ===== */
.stTabs [data-baseweb="tab-list"]::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    height: 2px;
    background: var(--accent);
    transition: all var(--transition-base);
}

/* ===== 文件上传拖拽效果 ===== */
[data-testid="stFileUploader"]:hover {
    animation: pulse 2s ease-in-out infinite;
}

[data-testid="stFileUploader"] section {
    transition: all var(--transition-base) !important;
}

/* ===== 侧边栏底部渐变遮罩 ===== */
[data-testid="stSidebar"]::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 60px;
    background: linear-gradient(to top, var(--bg-sidebar) 0%, transparent 100%);
    pointer-events: none;
}

/* ===== 加载状态骨架屏效果 ===== */
.stSpinner > div {
    border-color: var(--accent-light) !important;
    border-top-color: var(--accent) !important;
}

/* ===== 工具提示增强 ===== */
[data-baseweb="tooltip"] {
    background: var(--primary-800) !important;
    color: white !important;
    border-radius: var(--radius-md) !important;
    font-size: 0.8125rem !important;
    padding: var(--space-sm) var(--space-md) !important;
    box-shadow: var(--shadow-lg) !important;
}

/* ===== 选中文字样式 ===== */
::selection {
    background: var(--accent-light);
    color: var(--accent-hover);
}

/* ===== 禁用状态统一样式 ===== */
*:disabled,
*[disabled] {
    opacity: 0.5 !important;
    cursor: not-allowed !important;
    filter: grayscale(20%);
}

/* ═══════════════════════════════════════════════════════════════
   入场动画与微交互
   ═══════════════════════════════════════════════════════════════ */

/* ===== 关键帧动画定义 ===== */
@keyframes fadeInUp {
    from {
        opacity: 0;
        transform: translateY(20px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
}

@keyframes slideInLeft {
    from {
        opacity: 0;
        transform: translateX(-20px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

@keyframes pulse {
    0%, 100% { transform: scale(1); }
    50% { transform: scale(1.02); }
}

@keyframes shimmer {
    0% { background-position: -200% 0; }
    100% { background-position: 200% 0; }
}

@keyframes glowPulse {
    0%, 100% { box-shadow: 0 0 5px rgba(37, 99, 235, 0.2); }
    50% { box-shadow: 0 0 20px rgba(37, 99, 235, 0.4); }
}

/* ===== 页面标题入场动画 ===== */
.main h1 {
    animation: fadeInUp 0.5s ease-out;
}

/* ===== 指标卡片入场动画 - 已在上方定义 ===== */
/* 动画已简化，避免 both 关键字导致的空白问题 */

/* ===== 按钮悬停增强动画 ===== */
.main .stButton > button:active {
    transform: translateY(1px) scale(0.98) !important;
}

/* ===== 消息提示入场动画 ===== */
.stAlert,
[data-testid="stAlert"] {
    animation: slideInLeft 0.3s ease-out;
}

/* ===== 表格行悬停动画 ===== */
[data-testid="stDataFrame"] tbody tr {
    transition: background-color 0.15s ease, transform 0.15s ease;
}

[data-testid="stDataFrame"] tbody tr:hover {
    background-color: var(--accent-lighter) !important;
    transform: translateX(2px);
}

/* ===== 卡片悬停呼吸效果 ===== */
[data-testid="stMetric"]:hover {
    animation: pulse 1s ease-in-out infinite;
}

/* ===== 加载骨架屏闪烁效果 ===== */
.loading-skeleton {
    background: linear-gradient(90deg,
        var(--primary-100) 25%,
        var(--primary-200) 50%,
        var(--primary-100) 75%
    );
    background-size: 200% 100%;
    animation: shimmer 1.5s infinite;
    border-radius: var(--radius-md);
}

/* ===== 输入框聚焦光晕动画 ===== */
.stTextInput input:focus,
.stTextArea textarea:focus {
    animation: glowPulse 2s ease-in-out infinite;
}

/* ===== 侧边栏项目入场动画 ===== */
[data-testid="stSidebar"] .stRadio > div[role="radiogroup"] > label {
    animation: fadeIn 0.3s ease-out;
}

/* ===== 文件上传区域悬停动画 ===== */
[data-testid="stFileUploader"]:hover {
    animation: pulse 0.5s ease-in-out;
}

/* ===== Tab切换动画 ===== */
.stTabs [data-baseweb="tab-panel"] {
    animation: fadeIn 0.2s ease-out;
}

/* ===== 进度条动画增强 ===== */
.stProgress > div > div > div > div {
    transition: width 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

/* ===== 数字增长动画效果 (指标卡片) ===== */
[data-testid="stMetricValue"] {
    transition: color 0.3s ease;
}

[data-testid="stMetric"]:hover [data-testid="stMetricValue"] {
    color: var(--accent) !important;
}

/* ===== 滚动条美化 ===== */
::-webkit-scrollbar {
    width: 8px;
    height: 8px;
}

::-webkit-scrollbar-track {
    background: var(--bg-elevated);
    border-radius: var(--radius-full);
}

::-webkit-scrollbar-thumb {
    background: var(--primary-300);
    border-radius: var(--radius-full);
    transition: background 0.2s ease;
}

::-webkit-scrollbar-thumb:hover {
    background: var(--primary-400);
}

/* ===== 焦点可见性增强 (无障碍) ===== */
*:focus-visible {
    outline: 2px solid var(--accent) !important;
    outline-offset: 2px !important;
}

/* ===== 平滑滚动 ===== */
html {
    scroll-behavior: smooth;
}

/* ═══════════════════════════════════════════════════════════════
   Premium UI Enhancements - Editorial Data Dashboard
   ═══════════════════════════════════════════════════════════════ */

/* ===== 高级光晕效果 - 指标卡片 ===== */
[data-testid="stMetric"]::after {
    content: '';
    position: absolute;
    top: 50%;
    left: 50%;
    width: 120%;
    height: 120%;
    background: radial-gradient(circle, rgba(37, 99, 235, 0.1) 0%, transparent 60%);
    transform: translate(-50%, -50%) scale(0);
    transition: transform 0.5s cubic-bezier(0.22, 1, 0.36, 1);
    pointer-events: none;
    z-index: 0;
}

[data-testid="stMetric"]:hover::after {
    transform: translate(-50%, -50%) scale(1);
}

/* ===== 侧边栏品牌标题 - Premium ===== */
[data-testid="stSidebar"] h1 {
    font-family: var(--font-display) !important;
    font-size: 1.125rem !important;
    font-weight: 800 !important;
    background: linear-gradient(135deg, var(--accent) 0%, #3B82F6 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    position: relative;
}

/* ===== 表格Premium样式 ===== */
[data-testid="stDataFrame"] {
    border-radius: var(--radius-xl) !important;
    overflow: hidden;
    box-shadow: 0 4px 24px -4px rgba(0, 0, 0, 0.08) !important;
}

[data-testid="stDataFrame"] th {
    font-family: var(--font-display) !important;
    background: linear-gradient(180deg, var(--bg-elevated) 0%, #E8ECF0 100%) !important;
    font-weight: 700 !important;
    font-size: 0.7rem !important;
    letter-spacing: 0.08em;
    border-bottom: 2px solid var(--border-default) !important;
}

/* ===== 按钮Premium效果 ===== */
.stButton > button {
    font-family: var(--font-display) !important;
    position: relative;
    overflow: hidden;
}

/* 按钮内部光效扫过 */
.stButton > button::after {
    content: '';
    position: absolute;
    top: 0;
    left: -100%;
    width: 100%;
    height: 100%;
    background: linear-gradient(90deg,
        transparent 0%,
        rgba(255, 255, 255, 0.2) 50%,
        transparent 100%);
    transition: left 0.5s ease;
}

.stButton > button:hover::after {
    left: 100%;
}

/* ===== 悬浮光标效果 ===== */
.main .stButton > button,
[data-testid="stMetric"],
[data-testid="stDataFrame"] tbody tr {
    cursor: pointer;
}

/* ===== 顶部装饰线 - 已禁用 ===== */
/* 彩虹渐变装饰线已移除，保持简洁风格 */

/* ===== 主内容区域入场动画编排 - 已简化 ===== */
.main .block-container > div > div {
    opacity: 1;
}

/* ===== 数据可视化容器 Premium ===== */
[data-testid="stVegaLiteChart"],
[data-testid="stPlotlyChart"] {
    background: rgba(255, 255, 255, 0.9) !important;
    backdrop-filter: blur(10px);
    border-radius: var(--radius-xl) !important;
    border: 1px solid rgba(255, 255, 255, 0.8) !important;
    box-shadow: 0 4px 24px -4px rgba(0, 0, 0, 0.06) !important;
    padding: var(--space-lg) !important;
}

/* ===== Alert消息Premium样式 ===== */
.stAlert,
[data-testid="stAlert"] {
    backdrop-filter: blur(10px);
    border-radius: var(--radius-lg) !important;
}

/* ===== 选择框Premium样式 ===== */
.stSelectbox > div > div,
.stMultiSelect > div > div {
    font-family: var(--font-sans) !important;
    border-radius: var(--radius-lg) !important;
    transition: all 0.2s ease !important;
}

.stSelectbox > div > div:hover,
.stMultiSelect > div > div:hover {
    border-color: var(--accent) !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1) !important;
}

/* ===== 输入框Premium样式 ===== */
.stTextInput input,
.stTextArea textarea {
    font-family: var(--font-sans) !important;
    border-radius: var(--radius-lg) !important;
}

/* ===== 小标题装饰 ===== */
.main h2::before {
    content: '';
    display: inline-block;
    width: 4px;
    height: 1.2em;
    background: linear-gradient(180deg, var(--accent) 0%, #60A5FA 100%);
    border-radius: 2px;
    margin-right: 0.75rem;
    vertical-align: middle;
}

/* ===== Tab导航Premium ===== */
.stTabs [data-baseweb="tab"] {
    font-family: var(--font-display) !important;
    font-weight: 600 !important;
}

.stTabs [aria-selected="true"] {
    background: linear-gradient(180deg, transparent 0%, rgba(37, 99, 235, 0.05) 100%) !important;
}

/* ===== 文件上传区域Premium ===== */
[data-testid="stFileUploader"] {
    background: linear-gradient(135deg,
        rgba(255, 255, 255, 0.9) 0%,
        rgba(248, 250, 252, 0.8) 100%) !important;
    backdrop-filter: blur(10px);
    border-radius: var(--radius-xl) !important;
}

[data-testid="stFileUploader"]:hover {
    background: linear-gradient(135deg,
        rgba(239, 246, 255, 0.95) 0%,
        rgba(219, 234, 254, 0.9) 100%) !important;
    border-color: var(--accent) !important;
}

/* ===== Expander Premium ===== */
.streamlit-expanderHeader {
    font-family: var(--font-display) !important;
    font-weight: 600 !important;
    border-radius: var(--radius-lg) !important;
}

/* ===== 加载动画Premium ===== */
@keyframes spin {
    to { transform: rotate(360deg); }
}

.stSpinner > div {
    border-width: 3px !important;
    animation: spin 0.8s linear infinite;
}

/* ===== 卡片内容层级确保 ===== */
[data-testid="stMetric"] > div {
    position: relative;
    z-index: 1;
}

/* ===== 响应式优化 ===== */
@media (max-width: 1024px) {
    .main::after {
        left: 0;
    }
}

@media (max-width: 768px) {
    [data-testid="stMetricValue"] {
        font-size: 1.75rem !important;
    }

    [data-testid="stMetric"] {
        padding: var(--space-md) var(--space-lg) !important;
    }
}
</style>
"""

# AI助手样式 - 成熟聊天窗体验
AI_ASSISTANT_CSS = """
<style>
div[data-testid="stPopoverBody"] {
    width: min(440px, calc(100vw - 32px)) !important;
    max-height: 82vh !important;
    border-radius: 20px !important;
    box-shadow: 0 28px 80px rgba(15, 23, 42, 0.24) !important;
    border: 1px solid rgba(148, 163, 184, 0.24) !important;
    padding: 16px 16px 14px !important;
    background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%) !important;
    overflow: hidden !important;
}

div[data-testid="stPopoverBody"] > div,
div[data-testid="stPopoverBody"] > div > div {
    padding: 0 !important;
    margin: 0 !important;
}

div[data-testid="stPopoverBody"] [data-testid="stVerticalBlock"] {
    gap: 0.75rem !important;
}

div[data-testid="stPopoverBody"] [data-testid="stVerticalBlockBorderWrapper"] {
    border: 1px solid rgba(191, 219, 254, 0.85) !important;
    border-radius: 18px !important;
    background: linear-gradient(180deg, rgba(248, 250, 252, 0.96) 0%, rgba(239, 246, 255, 0.96) 100%) !important;
    box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.7) !important;
}

div[data-testid="stPopoverBody"] [data-testid="stVerticalBlockBorderWrapper"] > div {
    padding: 0.35rem 0.45rem 0.35rem 0.5rem !important;
}

div[data-testid="stPopoverBody"] [data-testid="stChatMessage"] {
    padding: 0.4rem 0 !important;
    margin: 0 !important;
}

div[data-testid="stPopoverBody"] [data-testid="stChatInput"] {
    margin-top: 0.25rem !important;
    padding-top: 0.85rem !important;
    border-top: 1px solid rgba(226, 232, 240, 0.95) !important;
    background: transparent !important;
}

div[data-testid="stPopoverBody"] [data-testid="stChatInput"] textarea {
    min-height: 52px !important;
    border-radius: 16px !important;
    border: 1px solid rgba(148, 163, 184, 0.42) !important;
    padding: 12px 14px !important;
    font-size: 0.95rem !important;
    box-shadow: none !important;
    background: rgba(255, 255, 255, 0.95) !important;
}

div[data-testid="stPopoverBody"] [data-testid="stChatInput"] textarea:focus,
div[data-testid="stPopoverBody"] [data-testid="stChatInput"] textarea:focus-visible {
    border-color: rgba(37, 99, 235, 0.45) !important;
    box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.12) !important;
    outline: none !important;
}

div[data-testid="stPopoverBody"] [data-testid="stChatInput"] button {
    width: 44px !important;
    height: 44px !important;
    border-radius: 14px !important;
    border: none !important;
    background: linear-gradient(135deg, #2563eb 0%, #1d4ed8 100%) !important;
    box-shadow: 0 14px 24px rgba(37, 99, 235, 0.24) !important;
}

div[data-testid="stPopoverBody"] [data-testid="stChatInput"] button svg,
div[data-testid="stPopoverBody"] [data-testid="stChatInput"] button path {
    fill: #ffffff !important;
    color: #ffffff !important;
}

div[data-testid="stPopoverBody"] .stButton > button {
    min-height: 40px !important;
    border-radius: 14px !important;
    font-size: 0.88rem !important;
    font-weight: 600 !important;
}

.ai-chat-shell {
    display: block;
}

.ai-chat-header {
    padding: 0.95rem 1rem;
    border-radius: 18px;
    background: linear-gradient(135deg, rgba(30, 64, 175, 0.95) 0%, rgba(37, 99, 235, 0.92) 58%, rgba(14, 165, 233, 0.88) 100%);
    color: #ffffff;
    box-shadow: 0 18px 34px rgba(30, 64, 175, 0.26);
}

.ai-chat-header-title {
    font-size: 1rem;
    font-weight: 700;
    letter-spacing: 0.01em;
}

.ai-chat-header-subtitle {
    margin-top: 0.35rem;
    font-size: 0.82rem;
    line-height: 1.5;
    color: rgba(255, 255, 255, 0.88);
}

.ai-chat-empty-state {
    padding: 0.95rem 0.2rem 0.15rem;
}

.ai-chat-empty-title {
    font-size: 0.98rem;
    font-weight: 700;
    color: #0f172a;
}

.ai-chat-empty-subtitle {
    margin-top: 0.42rem;
    font-size: 0.88rem;
    line-height: 1.65;
    color: #475569;
}

.ai-chat-empty-hint {
    margin-top: 0.62rem;
    font-size: 0.8rem;
    line-height: 1.55;
    color: #64748b;
}

.ai-chat-quick-grid {
    display: grid;
    gap: 0.5rem;
    margin-top: 0.35rem;
}

.ai-chat-actions {
    margin-top: 0.15rem;
}

.ai-chat-thinking {
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.85rem 0.95rem;
    border-radius: 14px;
    border: 1px dashed rgba(59, 130, 246, 0.35);
    background: rgba(239, 246, 255, 0.86);
    color: #1e3a8a;
    font-size: 0.9rem;
    font-weight: 600;
}

.ai-chat-thinking::before {
    content: "";
    width: 0.55rem;
    height: 0.55rem;
    border-radius: 999px;
    background: linear-gradient(135deg, #2563eb 0%, #0ea5e9 100%);
    box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.12);
    animation: ai-chat-pulse 1.3s ease-in-out infinite;
}

.ai-chat-disclaimer {
    margin: 0;
    text-align: center;
    font-size: 0.75rem;
    color: #64748b;
}

@keyframes ai-chat-pulse {
    0%, 100% { transform: scale(0.9); opacity: 0.8; }
    50% { transform: scale(1.08); opacity: 1; }
}
</style>
"""


def inject_global_styles():
    """注入全局样式到Streamlit应用"""
    import streamlit as st

    st.markdown(GLOBAL_CSS, unsafe_allow_html=True)


def inject_ai_assistant_styles():
    """注入AI助手样式"""
    import streamlit as st

    st.markdown(AI_ASSISTANT_CSS, unsafe_allow_html=True)
