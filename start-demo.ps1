param(
  [switch]$Rebuild,
  [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $root '.venv\Scripts\python.exe'
$frontend = Join-Path $root 'frontend'
$distIndex = Join-Path $frontend 'dist\index.html'
$url = 'http://127.0.0.1:8000'

if (-not (Test-Path -LiteralPath $python)) {
  throw "未找到 Python 虚拟环境：$python。请先创建 .venv 并安装 backend/requirements.txt。"
}

if ($Rebuild -or -not (Test-Path -LiteralPath $distIndex)) {
  Push-Location $frontend
  try {
    if (-not (Test-Path -LiteralPath (Join-Path $frontend 'node_modules'))) {
      npm ci --no-audit --no-fund
    }
    npm run build
  } finally {
    Pop-Location
  }
}

$listener = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
if (-not $listener) {
  $logDir = Join-Path $root 'logs'
  New-Item -ItemType Directory -Force -Path $logDir | Out-Null
  $process = Start-Process `
    -FilePath $python `
    -ArgumentList @('-m', 'backend', '--host', '127.0.0.1', '--port', '8000') `
    -WorkingDirectory $root `
    -WindowStyle Hidden `
    -RedirectStandardOutput (Join-Path $logDir 'demo.stdout.log') `
    -RedirectStandardError (Join-Path $logDir 'demo.stderr.log') `
    -PassThru

  $deadline = (Get-Date).AddSeconds(30)
  do {
    Start-Sleep -Milliseconds 500
    $listener = Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue
    if ($listener) { break }
    if ($process.HasExited) {
      throw "演示服务启动失败，请查看 logs\demo.stderr.log"
    }
  } while ((Get-Date) -lt $deadline)
}

if (-not $listener) {
  throw '演示服务未能在 30 秒内监听 8000 端口。'
}

$health = Invoke-RestMethod "$url/api/health" -TimeoutSec 8
Write-Host "城市智眼演示已启动：$url"
Write-Host "后端状态：$($health.status)"

if (-not $NoBrowser) {
  Start-Process $url
}
