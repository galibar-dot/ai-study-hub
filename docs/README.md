# 手机 ↔ 电脑 ↔ Claude

让手机通过电脑这个中转，跟你电脑上已登录的 Claude Code 聊天。

## 工作原理

```
手机浏览器  ──HTTP──>  电脑上的 FastAPI 服务  ──Agent SDK──>  Claude Code  ──>  Claude
```

- 电脑要开机、服务要在跑、Claude Code 要已登录
- 手机不用装任何 App，浏览器就行
- API Key 不用配，复用 Claude Code 的登录态

## 首次准备

依赖已经装好了。如果换机器，运行：

```powershell
pip install -r requirements.txt
```

并确认 Claude Code CLI 已装好且已登录：

```powershell
claude --version
claude  # 跑一次确认是登录状态
```

## 配置（必做一次）

打开 `server.py`，把顶部的 `PASSWORD` 改成你自己的密码：

```python
PASSWORD = "你自己的密码"
```

## 启动

双击 `start.bat`，或命令行运行：

```powershell
python server.py
```

看到 `Uvicorn running on http://0.0.0.0:8000` 就是好了。

## 三种访问方式

### 方式 1：本机自测
浏览器打开 `http://localhost:8000`

### 方式 2：同 WiFi 手机访问（最简单，只能在家）

1. 在电脑上查 IP：
   ```powershell
   ipconfig
   ```
   找到 "IPv4 地址"，类似 `192.168.1.123`

2. 手机连同一个 WiFi，浏览器打开 `http://192.168.1.123:8000`

3. **如果连不上**：Windows 防火墙拦了。打开 "Windows Defender 防火墙 → 允许应用通过防火墙"，给 Python 放行；或者用管理员 PowerShell 跑一次：
   ```powershell
   New-NetFirewallRule -DisplayName "Claude Chat" -Direction Inbound -Protocol TCP -LocalPort 8000 -Action Allow
   ```

### 方式 3：Cloudflare Tunnel 外网访问（在外也能用）

1. **装 cloudflared**（一次性）：
   - 下载 [cloudflared-windows-amd64.exe](https://github.com/cloudflare/cloudflared/releases/latest)
   - 改名为 `cloudflared.exe`，放到 `C:\Windows\` 或者本项目目录

2. **临时隧道（最快，重启就换地址）**：
   ```powershell
   cloudflared tunnel --url http://localhost:8000
   ```
   会输出一个 `https://xxxx-xxxx-xxxx.trycloudflare.com` 地址，手机访问就行。
   缺点：每次重启地址都变。

3. **固定地址（推荐，需要 Cloudflare 账号+一个域名）**：
   - 在 [Cloudflare Dashboard](https://one.dash.cloudflare.com/) → Zero Trust → Networks → Tunnels 新建隧道
   - 按引导跑一行 `cloudflared service install <token>`
   - 在 Public Hostname 里加一条：`chat.你的域名.com` → `http://localhost:8000`
   - 手机访问 `https://chat.你的域名.com`，永久固定

## 项目结构

```
claude code1/
├── server.py           # FastAPI 后端
├── requirements.txt    # Python 依赖
├── start.bat           # Windows 一键启动
├── README.md           # 本文件
└── static/
    └── index.html      # 聊天网页
```

## 常用操作

- **新对话**：网页右上角 "新对话" 按钮，清空上下文
- **退出登录**：清浏览器 cookie 即可
- **改模型**：编辑 `server.py` 顶部 `MODEL` 变量，可选：
  - `claude-opus-4-7`（默认，最强）
  - `claude-sonnet-4-6`（快、省）
  - `claude-haiku-4-5-20251001`（最快最便宜）

## 安全提示

- **密码一定要改**，默认密码 `change-me-please` 太弱
- 用 Cloudflare Tunnel 外网暴露时，密码是唯一防线
- 服务跑在 `0.0.0.0`，同 WiFi 任何人都能连，所以密码不能省
- 该服务**禁用了所有工具**（不能执行 bash、读写文件），纯聊天，比较安全

## 排查

| 现象 | 原因 / 解决 |
|---|---|
| 启动报 `claude` not found | Claude Code CLI 没装；先 `npm install -g @anthropic-ai/claude-code` |
| 启动报 unauthorized | Claude Code 没登录；先在电脑上跑一次 `claude` 登录 |
| 手机访问超时 | 防火墙；见上面 "方式 2" 第 3 步 |
| 回复一直转圈 | 看电脑端命令行有没有报错；最常见是 API 限流或网络 |
| 多轮上下文丢了 | 用了 "新对话" 按钮，或者电脑端服务重启过 |
