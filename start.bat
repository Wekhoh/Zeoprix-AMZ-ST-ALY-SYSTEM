@echo off
chcp 65001 >nul
title AMZ搜索词分析系统

echo ========================================
echo   AMZ搜索词分析系统 启动器
echo ========================================
echo.

:: 检查Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [错误] 未找到Python，请先安装Python 3.10+
    pause
    exit /b 1
)

:: 切换到脚本所在目录
cd /d "%~dp0"

:: 检查依赖
echo [1/3] 检查依赖...
pip show streamlit >nul 2>&1
if errorlevel 1 (
    echo [提示] 正在安装依赖，请稍候...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [错误] 依赖安装失败
        pause
        exit /b 1
    )
)

:: 检查.env文件
echo [2/3] 检查配置...
if not exist ".env" (
    echo [提示] 未找到.env文件，正在创建...
    copy .env.example .env >nul
    echo [警告] 请编辑.env文件，配置GEMINI_API_KEY
    notepad .env
)

:: 启动应用
echo [3/3] 启动应用...
echo.
echo 应用将在浏览器中打开: http://localhost:8501
echo 按 Ctrl+C 可停止应用
echo.

streamlit run src/app.py

pause
