# 问题排查指南

本文档记录开发和使用过程中遇到的问题及解决方案。

## 安装问题

### 问题: pip install 失败

**症状**: 运行 `pip install -r requirements.txt` 时报错

**解决方案**:
1. 确保使用 Python 3.10+
```bash
python --version
```

2. 升级 pip
```bash
python -m pip install --upgrade pip
```

3. 使用国内镜像（中国用户）
```bash
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

### 问题: google-genai 安装失败

**症状**: 安装 google-genai 时报依赖冲突

**解决方案**:
```bash
# 先卸载旧版本
pip uninstall google-generativeai google-genai -y

# 安装新版本
pip install google-genai>=1.0.0
```

**注意**: `google-genai` 是新版SDK，不要使用已废弃的 `google-generativeai`。

## 运行问题

### 问题: 双击start.bat后窗口闪退

**症状**: 双击 start.bat 后窗口立即关闭，看不到任何内容

**根因**: 批处理文件中包含中文字符，Windows CMD默认使用GBK编码，而文件保存为UTF-8，导致中文被解析为乱码命令

**解决方案**:
start.bat 已修复，使用纯英文内容。如果仍有问题：
1. 右键 start.bat → 编辑
2. 确认文件内容为英文
3. 或使用 PowerShell 运行 start.ps1

### 问题: Streamlit 启动失败 (ModuleNotFoundError)

**症状**: `ModuleNotFoundError: No module named 'src'`

**解决方案**:
使用 start.bat 启动，它会自动设置 PYTHONPATH。
如需手动运行：
```bash
cd "C:\Users\你的用户名\桌面\AMZ搜索词分析系统"
set PYTHONPATH=%CD%
streamlit run src/app.py
```

### 问题: AttributeError: 'Settings' object has no attribute 'db_path'

**症状**: 应用启动后浏览器显示 AttributeError

**根因**: 代码中使用了错误的属性名 `settings.db_path`，正确名称是 `settings.database_path`

**解决方案**:
此问题已在 v1.0.1 修复。如仍遇到：
1. 检查 `src/app.py` 第26行
2. 确保使用 `settings.database_path` 而非 `settings.db_path`

### 问题: AttributeError: 'Database' object has no attribute 'get_products'

**症状**: 应用启动后浏览器显示 AttributeError: get_products

**根因**: 代码中使用了错误的方法名 `db.get_products()`，正确名称是 `db.get_all_products()`

**解决方案**:
此问题已在 v1.0.1 修复。如仍遇到：
1. 检查 `src/app.py` 第55行
2. 确保使用 `db.get_all_products()` 而非 `db.get_products()`

### 问题: Streamlit 启动失败 (旧版)

**症状**: `ModuleNotFoundError: No module named 'src'`

**解决方案**:
确保从项目根目录运行：
```bash
cd "C:\Users\你的用户名\桌面\AMZ搜索词分析系统"
streamlit run src/app.py
```

### 问题: 数据库初始化失败

**症状**: "数据库未初始化" 错误

**解决方案**:
1. 确保 `data/db/` 目录存在
```bash
mkdir data\\db
```

2. 检查目录权限
3. 删除损坏的数据库文件后重启

### 问题: 文件编码错误

**症状**: 上传CSV文件时出现乱码或解析失败

**解决方案**:
系统自动尝试多种编码（UTF-8, GBK, GB2312, Latin-1）。如仍失败：
1. 用Excel打开CSV，另存为 "UTF-8 CSV"
2. 或直接使用Excel格式（.xlsx）

## API问题

### 问题: Gemini API 调用失败

**症状**: "AI分析失败" 或 API 超时

**解决方案**:
1. 检查 .env 文件中的 API Key
```bash
# .env 内容示例
GEMINI_API_KEY=AIza...你的密钥
```

2. 验证 API Key 是否有效
```python
from google import genai
client = genai.Client(api_key="你的密钥")
response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents="Hello"
)
print(response.text)
```

3. 检查网络连接和代理设置

4. 如果是配额问题，等待重置或申请更高配额

### 问题: API Key 被拒绝

**症状**: "Invalid API key" 或 "Permission denied"

**解决方案**:
1. 确认密钥来源正确: [Google AI Studio](https://makersuite.google.com/app/apikey)
2. 检查密钥是否启用
3. 确认账户没有被限制

## 测试问题

### 问题: NumPy 布尔值比较失败

**症状**: `assert result is True` 失败，因为 `np.True_ is not True`

**解决方案**:
使用 `==` 而不是 `is` 进行比较：
```python
# 错误
assert result is True

# 正确
assert result == True
```

### 问题: 测试fixture 找不到方法

**症状**: `'Database' object has no attribute 'xxx'`

**解决方案**:
检查 Database 类的实际方法名：
```python
# 错误: batch_insert_search_terms
# 正确: save_search_terms(df, campaign_id)

# 错误: campaign_type
# 正确: match_type
```

### 问题: 测试需要 API Key

**症状**: 部分测试被跳过

**解决方案**:
设置环境变量后运行测试：
```bash
# Windows
set GEMINI_API_KEY=你的密钥
python -m pytest tests/ -v

# macOS/Linux
export GEMINI_API_KEY=你的密钥
python -m pytest tests/ -v
```

## 规则引擎问题

### 问题: 核心词被错误分类为"低相关性" (BUG-001/003)

**症状**: 明显的核心词（如 "neck pillow"）被规则引擎判断为"低相关性"，建议否定

**根因**:
1. 人工标记的相关性等级（如 `strong_core`）未正确映射到规则匹配时的类别（`strong`）
2. `_match_rule()` 函数直接比较原始值，没有调用 `RelevanceLevel.to_category()`

**解决方案**:
在 `src/rules/engine.py` 的 `_match_rule()` 函数中添加类别转换：
```python
# 修复后的代码
actual_category = RelevanceLevel.to_category(actual_relevance) if actual_relevance else None
if actual_category != required_relevance:
    return False
```

**相关性等级映射关系**:
| 原始等级 | 映射类别 |
|---------|---------|
| strong_core | strong |
| strong_longtail | strong |
| weak | weak |
| generic | generic |
| irrelevant | irrelevant |

### 问题: 强相关高ACOS词被建议否定 (BUG-002)

**症状**: 强相关但ACOS较高的词被"低转化高花费"规则匹配，建议否定

**根因**: "低转化高花费"规则没有排除强相关词的条件

**解决方案**:
1. 在规则引擎中添加 `relevance_not` 条件支持
2. 更新规则条件，添加 `relevance_not: strong`

```python
# engine.py 中添加 relevance_not 支持
if "relevance_not" in conditions:
    excluded = conditions["relevance_not"]
    if actual_category == excluded:
        return False  # 排除匹配
```

### 问题: 导出数据不完整，缺少部分搜索词 (BUG-004)

**症状**: 导出的Excel/CSV文件缺少部分搜索词（如145条缺失，覆盖率仅68.5%）

**根因**:
1. `export_results()` 使用 `db.get_analysis_results()` 读取数据库
2. `save_analysis_result_by_term()` 使用 `LIMIT 1`，同词跨活动只保存第一条
3. 数据库中的分析结果不完整

**解决方案**:
修改 `src/ui/pages/analysis.py` 的 `export_results()` 函数，使用实时计算代替数据库读取：
```python
# 修复后 - 使用实时计算
from src.rules.engine import analyze_search_terms
raw_results = analyze_search_terms(db, product_id)

# 修复前 - 读取不完整的数据库
# results = db.get_analysis_results(product_id)
```

**验证方法**:
- UI显示的数据量应与导出的数据量一致
- 核心词（如 "neck pillow"）应包含在导出结果中

### 问题: 待审核数量与上传数量不一致 (常见疑问)

**症状**: 上传461条数据，但待审核只显示316条

**这不是Bug**，而是系统的正确行为：

| 计数类型 | 数据表 | 说明 |
|---------|-------|------|
| 原始记录数 (461) | search_terms | 每个CSV的每行一条记录，同一词在不同活动重复出现 |
| 唯一搜索词 (316) | manual_reviews | 去重后的唯一词，每词只需审核一次 |

**为什么这样设计**:
1. 同一个词（如 "travel pillow"）可能出现在多个广告活动中
2. 对同一个词只需要审核一次相关性
3. 审核结果会自动应用到该词在所有活动中的分析

**如何验证**:
```sql
-- 查看原始记录数
SELECT COUNT(*) FROM search_terms st
JOIN campaigns c ON st.campaign_id = c.id
WHERE c.product_id = 1;  -- 461

-- 查看唯一词数
SELECT COUNT(DISTINCT st.term) FROM search_terms st
JOIN campaigns c ON st.campaign_id = c.id
WHERE c.product_id = 1;  -- 316
```

## 功能问题

### 问题: 批量上传部分文件失败

**症状**: 批量上传多个文件时，部分文件显示"解析失败"

**解决方案**:
1. 检查失败文件的格式是否正确（CSV或Excel）
2. 确认文件未被其他程序占用
3. 尝试用Excel重新保存为UTF-8 CSV格式
4. 单独上传失败的文件排查问题

### 问题: 清空数据后无法恢复

**症状**: 点击"清空所有搜索词数据"后想要恢复

**解决方案**:
⚠️ 清空操作不可逆！建议：
1. 清空前先使用"导出完整数据备份"功能
2. 备份文件保存在安全位置
3. 如需恢复，重新上传原始CSV文件

### 问题: 分析结果为空

**症状**: 运行分析后没有结果显示

**解决方案**:
1. 确认已上传数据
2. 检查筛选条件是否过于严格
3. 检查规则阈值设置是否合理
4. 在设置中点击 "重新运行分析"

### 问题: 导出文件打开乱码

**症状**: Excel文件中文显示为乱码

**解决方案**:
1. 不要用记事本打开 .xlsx 文件
2. 用 Excel 或 WPS 打开
3. 对于 CSV 文件，用 Excel 导入功能选择 UTF-8 编码

### 问题: 配置回滚无效

**症状**: 点击回滚后配置未恢复

**解决方案**:
1. 确认 rule_versions 表中有版本记录
2. 刷新页面后查看
3. 检查浏览器控制台是否有错误

## 性能问题

### 问题: 处理大文件很慢

**症状**: 上传或分析大文件时界面卡顿

**解决方案**:
1. 建议单次上传不超过1万行
2. 按广告活动拆分文件
3. 增加本地内存

### 问题: 页面加载缓慢

**症状**: Streamlit 页面响应慢

**解决方案**:
1. 减少同时打开的标签页
2. 清理浏览器缓存
3. 重启 Streamlit 服务

## UI/CSS问题

### 问题: Streamlit组件CSS样式不生效

**症状**: 写了CSS但Streamlit组件样式没有变化

**根因**: Streamlit组件使用动态生成的class名和`data-testid`属性，普通CSS选择器无法匹配

**解决方案**:
1. 使用浏览器开发者工具检查元素，找到`data-testid`属性
2. 使用属性选择器：`[data-testid="stChatInput"]`
3. 常用Streamlit组件的data-testid：
   - 聊天输入框：`stChatInput`
   - 列容器：`stColumn`
   - 按钮：`stButton`
   - 侧边栏：`stSidebar`
4. 添加`!important`确保优先级

**示例**:
```css
/* 错误 - 无法匹配 */
.chat-input { border: none; }

/* 正确 - 使用data-testid */
[data-testid="stChatInput"] input {
    border: none !important;
}
```

### 问题: Streamlit输入框蓝色焦点边框无法移除

**症状**: 输入框聚焦时出现蓝色边框线，CSS设置`outline:none`无效

**根因**: Streamlit使用多层嵌套元素和伪元素，焦点样式可能在内层元素或`::before`/`::after`上

**解决方案**:
```css
/* 需要同时处理多个层级和伪元素 */
[data-testid="stChatInput"] *:focus,
[data-testid="stChatInput"] *:focus-visible,
[data-testid="stChatInput"] *:focus-within {
    outline: none !important;
    box-shadow: none !important;
    border-color: transparent !important;
}

/* 处理伪元素 */
[data-testid="stChatInput"] *::before,
[data-testid="stChatInput"] *::after {
    border: none !important;
    box-shadow: none !important;
}
```

### 问题: Streamlit按钮内SVG图标颜色无法修改

**症状**: 想修改按钮内箭头/图标颜色，设置`color`无效

**根因**: SVG图标使用`fill`属性而非`color`

**解决方案**:
```css
/* 修改SVG填充色 */
button svg path {
    fill: white !important;
}

/* 或使用currentColor让SVG继承color */
button svg {
    fill: currentColor;
}
```

### 问题: CSS选择器优先级不够

**症状**: 样式被Streamlit默认样式覆盖

**解决方案**:
1. 添加`!important`
2. 使用更具体的选择器
3. 使用`[data-testid]`属性选择器提高特异性
4. 在`st.markdown(unsafe_allow_html=True)`中注入`<style>`标签

### 问题: Streamlit popover/对话框内容贴边无内距

**症状**: `st.popover`弹出框内的文字紧贴边缘，没有内边距，看起来很拥挤

**根因**: Streamlit popover默认内边距较小，需要手动添加padding

**解决方案**:
```css
/* 方法1: 给popover容器添加内边距 */
[data-testid="stPopover"] > div {
    padding: 16px !important;
}

/* 方法2: 给popover内的特定元素添加内边距 */
[data-testid="stPopover"] .stMarkdown {
    padding: 12px 16px !important;
}

/* 方法3: 在popover内使用容器包装 */
```

**Python代码方案**:
```python
with st.popover("AI助手"):
    # 使用container添加间距
    with st.container():
        st.markdown("""
        <div style="padding: 16px;">
            内容区域
        </div>
        """, unsafe_allow_html=True)
```

### 问题: Streamlit组件间距不一致

**症状**: 页面元素之间间距大小不统一，视觉上不协调

**解决方案**:
1. 使用CSS变量统一管理间距
2. 对特定组件设置margin/padding
3. 使用`st.container()`包装元素控制间距

```css
/* 统一间距变量 */
:root {
    --spacing-sm: 8px;
    --spacing-md: 16px;
    --spacing-lg: 24px;
}

/* 应用到组件 */
.stButton {
    margin-bottom: var(--spacing-md) !important;
}
```

## 开发问题

### 问题: 代码修改后不生效

**症状**: 修改代码后界面没有变化

**解决方案**:
1. Streamlit 自动重载，等待几秒
2. 如未自动重载，按 R 键刷新
3. 重启 Streamlit 服务

### 问题: Git 提交警告 CRLF

**症状**: `warning: LF will be replaced by CRLF`

**解决方案**:
这是 Windows/Unix 换行符差异，不影响功能。如需消除警告：
```bash
git config --global core.autocrlf true
```

---

如遇到文档中未列出的问题，请：
1. 查看日志文件
2. 检查浏览器开发者工具控制台
3. 搜索错误信息
4. 提交 Issue
