# AMZ搜索词分析系统 PowerShell启动脚本
# 使用方法: 右键 -> 使用PowerShell运行

$Host.UI.RawUI.WindowTitle = "AMZ搜索词分析系统"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AMZ搜索词分析系统 启动器" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 切换到脚本目录
Set-Location $PSScriptRoot

# 检查Python
try {
    $pythonVersion = python --version 2>&1
    Write-Host "[OK] $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "[错误] 未找到Python，请先安装Python 3.10+" -ForegroundColor Red
    Read-Host "按回车键退出"
    exit 1
}

# 检查依赖
Write-Host "[1/3] 检查依赖..." -ForegroundColor Yellow
$streamlit = pip show streamlit 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[提示] 正在安装依赖，请稍候..." -ForegroundColor Yellow
    pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[错误] 依赖安装失败" -ForegroundColor Red
        Read-Host "按回车键退出"
        exit 1
    }
}
Write-Host "[OK] 依赖已安装" -ForegroundColor Green

# 检查.env文件
Write-Host "[2/3] 检查配置..." -ForegroundColor Yellow
if (-not (Test-Path ".env")) {
    Write-Host "[提示] 创建.env配置文件..." -ForegroundColor Yellow
    Copy-Item ".env.example" ".env"
    Write-Host "[警告] 请编辑.env文件，配置GEMINI_API_KEY" -ForegroundColor Yellow
    notepad .env
    Read-Host "配置完成后按回车键继续"
}
Write-Host "[OK] 配置文件就绪" -ForegroundColor Green

# 设置Python路径（解决模块导入问题）
$env:PYTHONPATH = $PSScriptRoot

# 启动应用
Write-Host "[3/3] 启动应用..." -ForegroundColor Yellow
Write-Host ""
Write-Host "应用将在浏览器中打开: http://localhost:8501" -ForegroundColor Cyan
Write-Host "按 Ctrl+C 可停止应用" -ForegroundColor Cyan
Write-Host ""

streamlit run src/app.py
