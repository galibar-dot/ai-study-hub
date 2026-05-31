# 开源前快速清理脚本
# 在项目根目录运行此脚本

Write-Host "=== 开源前数据清理 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 清理用户数据
Write-Host "1. 清理用户数据..." -ForegroundColor Yellow
if (Test-Path "chats") {
    Remove-Item -Recurse -Force "chats\*" -ErrorAction SilentlyContinue
    Write-Host "   ✓ 已清理 chats/" -ForegroundColor Green
}

if (Test-Path "logs") {
    Remove-Item -Recurse -Force "logs\*" -ErrorAction SilentlyContinue
    Write-Host "   ✓ 已清理 logs/" -ForegroundColor Green
}

if (Test-Path "__pycache__") {
    Remove-Item -Recurse -Force "__pycache__" -ErrorAction SilentlyContinue
    Write-Host "   ✓ 已清理 __pycache__/" -ForegroundColor Green
}

# 2. 删除敏感配置文件
Write-Host "`n2. 删除敏感配置..." -ForegroundColor Yellow
if (Test-Path "config.yml") {
    Remove-Item -Force "config.yml" -ErrorAction SilentlyContinue
    Write-Host "   ✓ 已删除 config.yml" -ForegroundColor Green
}

if (Test-Path ".env") {
    Remove-Item -Force ".env" -ErrorAction SilentlyContinue
    Write-Host "   ✓ 已删除 .env" -ForegroundColor Green
}

# 3. 删除用户数据库
Write-Host "`n3. 清理数据库..." -ForegroundColor Yellow
Get-ChildItem -Filter "*.db" | Where-Object { $_.Name -ne "ecdict.db" } | ForEach-Object {
    Remove-Item -Force $_.FullName -ErrorAction SilentlyContinue
    Write-Host "   ✓ 已删除 $($_.Name)" -ForegroundColor Green
}

# 4. 检查大文件
Write-Host "`n4. 检查大文件..." -ForegroundColor Yellow
$largeFiles = Get-ChildItem -File -Recurse | Where-Object { $_.Length -gt 10MB }
if ($largeFiles) {
    Write-Host "   ⚠️  发现大文件:" -ForegroundColor Red
    $largeFiles | ForEach-Object {
        $sizeMB = [math]::Round($_.Length/1MB, 2)
        Write-Host "      - $($_.Name) ($sizeMB MB)" -ForegroundColor Red
    }
    Write-Host "   提示: 确保这些文件在 .gitignore 中" -ForegroundColor Yellow
} else {
    Write-Host "   ✓ 没有发现大文件" -ForegroundColor Green
}

# 5. 检查敏感信息
Write-Host "`n5. 检查敏感信息..." -ForegroundColor Yellow
$passwordLine = Select-String -Path "server.py" -Pattern 'PASSWORD\s*=\s*["\'].*["\']' | Select-Object -First 1
if ($passwordLine) {
    Write-Host "   ⚠️  在 server.py 中发现密码:" -ForegroundColor Red
    Write-Host "      $($passwordLine.Line.Trim())" -ForegroundColor Red
    Write-Host "   建议: 修改为默认值或使用环境变量" -ForegroundColor Yellow
}

Write-Host "`n=== 清理完成 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "下一步:" -ForegroundColor Yellow
Write-Host "1. 检查 server.py 中的密码是否为默认值"
Write-Host "2. 确认 .gitignore 配置正确"
Write-Host "3. 运行 'git status' 检查将要提交的文件"
Write-Host "4. 创建 Git 仓库并推送到 GitHub"
Write-Host ""
