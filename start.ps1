# AMZ搜索词分析系统 PowerShell启动脚本（新版前后端工作台）
param(
    [switch]$NoBrowser,
    [switch]$ForceRestart
)

$ErrorActionPreference = 'Stop'
$Host.UI.RawUI.WindowTitle = 'AMZ搜索词分析系统（新版工作台）'

$RepoRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$FrontendDir = Join-Path $RepoRoot 'frontend'
$LogsDir = Join-Path $RepoRoot 'logs'
$BackendPort = 8008
$FrontendPort = 3031
$BackendUrl = "http://127.0.0.1:$BackendPort"
$FrontendUrl = "http://127.0.0.1:$FrontendPort"
$BackendLog = Join-Path $LogsDir 'backend-modern.log'
$BackendErrLog = Join-Path $LogsDir 'backend-modern.err.log'
$FrontendLog = Join-Path $LogsDir 'frontend-modern.log'
$FrontendErrLog = Join-Path $LogsDir 'frontend-modern.err.log'
$PythonExe = 'C:/Users/jackl/AppData/Local/Programs/Python/Python314/python.exe'

function Write-Stage([string]$label, [string]$message, [ConsoleColor]$color = 'Yellow') {
    Write-Host "[$label] $message" -ForegroundColor $color
}

function Test-Http([string]$url) {
    try {
        $response = Invoke-WebRequest -UseBasicParsing -Uri $url -TimeoutSec 2
        return $response.StatusCode -ge 200 -and $response.StatusCode -lt 500
    } catch {
        return $false
    }
}

function Get-ProcessesOnPort([int]$port) {
    $connections = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
    foreach ($conn in $connections) {
        $processId = $conn.OwningProcess
        try {
            $proc = Get-CimInstance Win32_Process -Filter "ProcessId = $processId"
            if ($proc) { $proc }
        } catch {
            continue
        }
    }
}

function Stop-RepoProcessOnPort([int]$port) {
    $repoPattern = [regex]::Escape($RepoRoot)
    foreach ($proc in Get-ProcessesOnPort -port $port) {
        $commandLine = [string]$proc.CommandLine
        if ($commandLine -match $repoPattern -or $commandLine -match 'next start' -or $commandLine -match 'uvicorn src.backend.app:app') {
            Write-Stage 'CLEAN' "停止占用端口 $port 的旧进程 PID $($proc.ProcessId)" 'DarkYellow'
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
        }
    }
}

function Wait-ForHttp([string]$url, [int]$timeoutSeconds = 45) {
    $deadline = (Get-Date).AddSeconds($timeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        if (Test-Http $url) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    }
    return $false
}

Set-Location $RepoRoot
if (-not (Test-Path $LogsDir)) {
    New-Item -ItemType Directory -Path $LogsDir | Out-Null
}

Write-Host '========================================' -ForegroundColor Cyan
Write-Host '  AMZ搜索词分析系统（新版工作台）' -ForegroundColor Cyan
Write-Host '========================================' -ForegroundColor Cyan
Write-Host ''

Write-Stage '1/5' '检查 Python 与 Node 环境'
if (-not (Test-Path $PythonExe)) {
    throw '未找到 Python 3.14，可执行文件路径失效。'
}
& $PythonExe --version | Out-Host
npm --version | Out-Host

Write-Stage '2/5' '准备依赖与环境变量'
$env:PYTHONPATH = $RepoRoot
if (-not (Test-Path (Join-Path $RepoRoot '.env')) -and (Test-Path (Join-Path $RepoRoot '.env.example'))) {
    Copy-Item (Join-Path $RepoRoot '.env.example') (Join-Path $RepoRoot '.env')
    Write-Stage 'WARN' '已创建 .env，请后续补齐必要配置。' 'Yellow'
}
if (-not (Test-Path (Join-Path $FrontendDir 'node_modules'))) {
    Write-Stage 'INFO' 'frontend/node_modules 不存在，开始 npm install' 'DarkYellow'
    Set-Location $FrontendDir
    npm install
    Set-Location $RepoRoot
}

Write-Stage '3/5' '停止旧版前后端占用并重新构建新版前端'
Stop-RepoProcessOnPort -port $BackendPort
Stop-RepoProcessOnPort -port $FrontendPort
if (Test-Path (Join-Path $FrontendDir '.next')) {
    Remove-Item -Recurse -Force (Join-Path $FrontendDir '.next') -ErrorAction SilentlyContinue
}
Set-Location $FrontendDir
npm run build | Out-Host
Set-Location $RepoRoot

Write-Stage '4/5' '启动 FastAPI 后端'
foreach ($log in @($BackendLog, $BackendErrLog, $FrontendLog, $FrontendErrLog)) {
    if (Test-Path $log) { Remove-Item $log -Force -ErrorAction SilentlyContinue }
}
$backendArgs = @('-m', 'uvicorn', 'src.backend.app:app', '--host', '127.0.0.1', '--port', "$BackendPort")
Start-Process -FilePath $PythonExe -ArgumentList $backendArgs -WorkingDirectory $RepoRoot -RedirectStandardOutput $BackendLog -RedirectStandardError $BackendErrLog -PassThru -WindowStyle Minimized | Out-Null
if (-not (Wait-ForHttp "$BackendUrl/frontend/workbench" 45)) {
    throw "后端启动失败，请查看日志：$BackendLog / $BackendErrLog"
}
Write-Stage 'OK' "后端已就绪：$BackendUrl" 'Green'

Write-Stage '5/5' '启动 Next 前端'
$frontendCmd = "set BACKEND_BASE_URL=$BackendUrl&& set NEXT_PUBLIC_BACKEND_BASE_URL=$BackendUrl&& npm run start -- --hostname 127.0.0.1 --port $FrontendPort"
Start-Process -FilePath 'cmd.exe' -ArgumentList '/c', $frontendCmd -WorkingDirectory $FrontendDir -RedirectStandardOutput $FrontendLog -RedirectStandardError $FrontendErrLog -PassThru -WindowStyle Minimized | Out-Null
Start-Sleep -Seconds 2
if (-not (Wait-ForHttp $FrontendUrl 60)) {
    Write-Stage 'WARN' "前端可能仍在启动，请查看日志：$FrontendLog / $FrontendErrLog" 'Yellow'
} else {
    Write-Stage 'OK' "前端已就绪：$FrontendUrl" 'Green'
}

Write-Host ''
Write-Host "新版工作台地址：$FrontendUrl" -ForegroundColor Cyan
Write-Host "后端接口地址：$BackendUrl" -ForegroundColor DarkCyan
Write-Host ''

if (-not $NoBrowser) {
    Start-Process $FrontendUrl
}
