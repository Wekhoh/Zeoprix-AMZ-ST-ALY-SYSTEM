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

### 问题: Streamlit 启动失败

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
mkdir -p data/db
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

## 功能问题

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
