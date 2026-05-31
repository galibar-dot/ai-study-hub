@echo off
setlocal enabledelayedexpansion
chcp 65001 >nul
echo ========================================
echo   AI Study Hub - Git Push Helper
echo ========================================
echo.

REM Check if in correct directory
if not exist "server.py" (
    echo Error: Please run this script in project root directory
    echo Current directory: %CD%
    pause
    exit /b 1
)

REM Check if Git is configured
git config user.name >nul 2>&1
if errorlevel 1 (
    echo [Step 1] Configure Git user information
    echo.
    set /p username="Enter your name: "
    set /p email="Enter your email: "
    git config --global user.name "!username!"
    git config --global user.email "!email!"
    echo.
    echo Git configuration completed
    echo.
) else (
    echo Git already configured
    for /f "tokens=*" %%i in ('git config user.name') do set gitname=%%i
    for /f "tokens=*" %%i in ('git config user.email') do set gitemail=%%i
    echo   Username: !gitname!
    echo   Email: !gitemail!
    echo.
)

REM Commit code
echo [Step 2] Commit code to local repository
echo.
git commit -m "Initial commit: AI Study Hub v1.0.0"
if errorlevel 1 (
    echo.
    echo Commit failed, please check error message
    pause
    exit /b 1
)
echo.
echo Code committed
echo.

REM Choose platform
echo [Step 3] Choose push platform
echo.
echo   [1] GitHub (International)
echo   [2] Gitee (China)
echo.
set /p choice="Please choose (1 or 2): "

if "%choice%"=="1" (
    echo.
    echo === Push to GitHub ===
    echo.
    echo Please create repository in browser first:
    echo https://github.com/new
    echo.
    echo Repository name: ai-study-hub
    echo Description: AI-powered learning platform
    echo Public/Private: Public
    echo Do NOT check "Add a README file"
    echo.
    pause
    echo.
    set /p ghuser="Enter your GitHub username: "
    echo.
    echo Linking remote repository...
    git remote add origin https://github.com/!ghuser!/ai-study-hub.git
    echo.
    echo Pushing code...
    echo Note: GitHub requires Personal Access Token, not password
    echo Get Token: https://github.com/settings/tokens
    echo.
    git branch -M main
    git push -u origin main
    echo.
    if errorlevel 1 (
        echo Push failed
        echo.
        echo Possible reasons:
        echo 1. Repository not created
        echo 2. Username incorrect
        echo 3. Need Personal Access Token (not password)
        echo.
        echo Get Token: https://github.com/settings/tokens
    ) else (
        echo.
        echo ========================================
        echo Push successful!
        echo ========================================
        echo.
        echo Repository URL: https://github.com/!ghuser!/ai-study-hub
        echo.
    )
) else if "%choice%"=="2" (
    echo.
    echo === Push to Gitee ===
    echo.
    echo Please create repository in browser first:
    echo https://gitee.com/projects/new
    echo.
    echo Repository name: ai-study-hub
    echo Description: AI-powered learning platform
    echo Public/Private: Public
    echo Do NOT check "Initialize with README"
    echo.
    pause
    echo.
    set /p gtuser="Enter your Gitee username: "
    echo.
    echo Linking remote repository...
    git remote add origin https://gitee.com/!gtuser!/ai-study-hub.git
    echo.
    echo Pushing code...
    git push -u origin master
    echo.
    if errorlevel 1 (
        echo Push failed
        echo.
        echo Possible reasons:
        echo 1. Repository not created
        echo 2. Username or password incorrect
    ) else (
        echo.
        echo ========================================
        echo Push successful!
        echo ========================================
        echo.
        echo Repository URL: https://gitee.com/!gtuser!/ai-study-hub
        echo.
    )
) else (
    echo.
    echo Invalid choice
)

echo.
echo ========================================
echo Press any key to exit...
pause >nul
