$ErrorActionPreference = "Continue"
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$exe = Join-Path $dir "cloudflared.exe"

if (-not (Test-Path $exe)) {
    Write-Host "  找不到 cloudflared.exe：$exe" -ForegroundColor Red
    Read-Host "  按回车退出"
    exit 1
}

$Host.UI.RawUI.WindowTitle = "Cloudflare Tunnel"

Write-Host ""
Write-Host "  启动 Cloudflare Tunnel..." -ForegroundColor Cyan
Write-Host "  约 3~10 秒后会出现公网地址" -ForegroundColor DarkGray
Write-Host ""

$found = $false

& $exe tunnel --url http://localhost:8000 --protocol http2 --no-autoupdate 2>&1 | ForEach-Object {
    $line = $_.ToString()
    if (-not $found -and $line -match 'https://[a-z0-9-]+\.trycloudflare\.com') {
        $url = $matches[0]
        $found = $true
        Write-Host ""
        Write-Host "  ============================================================" -ForegroundColor Green
        Write-Host "    公网地址 " -NoNewline -ForegroundColor Green
        Write-Host $url -ForegroundColor Yellow
        Write-Host "  ============================================================" -ForegroundColor Green
        try {
            Set-Clipboard -Value $url -ErrorAction Stop
            Write-Host "    （已复制到剪贴板）" -ForegroundColor DarkGray
        } catch {}
        Write-Host ""
        Write-Host "  关闭此窗口或 Ctrl+C 即停止隧道" -ForegroundColor DarkGray
        Write-Host ""
    } elseif ($found) {
        # 隧道起来之后，只显示明显的错误，正常心跳日志藏起来
        if ($line -match 'ERR|error|failed|disconnect') {
            Write-Host "  $line" -ForegroundColor Red
        }
    } else {
        # 还没拿到 URL 之前，全部低亮显示，方便排查
        Write-Host "  $line" -ForegroundColor DarkGray
    }
}
