# AI Study Hub - Git 提交和推送脚本
# 使用方法: 编辑此文件，填入你的 GitHub/Gitee 用户名和仓库地址，然后运行

Write-Host "=== AI Study Hub - Git 推送 ===" -ForegroundColor Cyan
Write-Host ""

# 1. 提交代码
Write-Host "1. 提交代码..." -ForegroundColor Yellow
git commit -m "Initial commit: AI Study Hub v1.0.0

Features:
- AI-powered chat with multiple model support
- English learning with ECDICT dictionary
- CET-6 reading comprehension practice
- Multi-platform access (desktop, mobile, remote)
- Web-based admin panel
- Local data storage for privacy"

if ($LASTEXITCODE -eq 0) {
    Write-Host "   ✓ 提交成功" -ForegroundColor Green
} else {
    Write-Host "   ✗ 提交失败" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "2. 选择推送平台:" -ForegroundColor Yellow
Write-Host "   [1] GitHub (国际)"
Write-Host "   [2] Gitee (国内)"
Write-Host ""
$choice = Read-Host "请选择 (1 或 2)"

if ($choice -eq "1") {
    # GitHub
    Write-Host ""
    Write-Host "推送到 GitHub..." -ForegroundColor Yellow
    Write-Host "请先在浏览器中创建仓库: https://github.com/new" -ForegroundColor Cyan
    Write-Host "仓库名: ai-study-hub" -ForegroundColor Cyan
    Write-Host ""
    $username = Read-Host "请输入你的 GitHub 用户名"
    
    Write-Host ""
    Write-Host "3. 关联远程仓库..." -ForegroundColor Yellow
    git remote add origin "https://github.com/$username/ai-study-hub.git"
    
    Write-Host ""
    Write-Host "4. 推送代码..." -ForegroundColor Yellow
    git branch -M main
    git push -u origin main
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ 推送成功!" -ForegroundColor Green
        Write-Host ""
        Write-Host "仓库地址: https://github.com/$username/ai-study-hub" -ForegroundColor Cyan
    }
    
} elseif ($choice -eq "2") {
    # Gitee
    Write-Host ""
    Write-Host "推送到 Gitee..." -ForegroundColor Yellow
    Write-Host "请先在浏览器中创建仓库: https://gitee.com/projects/new" -ForegroundColor Cyan
    Write-Host "仓库名: ai-study-hub" -ForegroundColor Cyan
    Write-Host ""
    $username = Read-Host "请输入你的 Gitee 用户名"
    
    Write-Host ""
    Write-Host "3. 关联远程仓库..." -ForegroundColor Yellow
    git remote add origin "https://gitee.com/$username/ai-study-hub.git"
    
    Write-Host ""
    Write-Host "4. 推送代码..." -ForegroundColor Yellow
    git push -u origin master
    
    if ($LASTEXITCODE -eq 0) {
        Write-Host ""
        Write-Host "✓ 推送成功!" -ForegroundColor Green
        Write-Host ""
        Write-Host "仓库地址: https://gitee.com/$username/ai-study-hub" -ForegroundColor Cyan
    }
    
} else {
    Write-Host "无效选择" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=== 完成 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "后续建议:" -ForegroundColor Yellow
Write-Host "  1. 添加项目截图到 README"
Write-Host "  2. 添加徽章 (Stars, License, Python version)"
Write-Host "  3. 在社区分享你的项目"
Write-Host "  4. 响应 Issues 和 Pull Requests"
Write-Host ""
