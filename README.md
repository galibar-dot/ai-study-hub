# AI Study Hub

[English](#english) | [中文](#中文)

---

## 中文

一个功能完整的 AI 聊天与学习平台，支持手机和电脑访问，包含智能对话、英语学习和阅读专项功能。

### ✨ 主要特性

- 🤖 **多模型支持** - 支持多种 AI 模型（Claude、GPT 等）
- 💬 **聊天功能** - 完整的对话历史、图片上传、PDF 文档支持
- 📚 **英语学习** - ECDICT 词典查询、生词本管理、学习统计
- 📖 **阅读专项** - CET-6 阅读理解练习、AI 生成文章、答题统计
- 📱 **多端访问** - 支持电脑、手机、外网访问
- 🛠️ **管理工具** - 命令行管理器 + 网页管理面板

### 🚀 快速开始

#### 1. 安装依赖

```bash
pip install -r requirements.txt
```

#### 2. 配置环境

```bash
# 复制配置文件
cp .env.example .env
cp config.yml.example config.yml

# 编辑 .env 设置密码
# APP_PASSWORD=your_secure_password
```

#### 3. 词典数据库
# 已经加入了词典数据库，学习模式下双击即可翻译单词

#### 4. 启动服务

**Windows:**
```bash
# 使用管理器（推荐）
admin_pannel.bat

# 或直接启动
start.bat
```

**Linux/Mac:**
```bash
python server.py
```

#### 5. 访问应用

- **聊天界面**: http://localhost:8000
- **管理面板**: http://localhost:8000/admin.html
- **默认密码**: `change-me-please` (请修改)

### 📱 手机访问

#### 同 WiFi 访问
1. 查看电脑 IP: `ipconfig` (Windows) 或 `ifconfig` (Linux/Mac)
2. 手机访问: `http://你的IP:8000`

#### 外网访问（Cloudflare Tunnel）

1. 运行: `cloudflared tunnel --url http://localhost:8000`
2. 使用生成的 URL 访问

### 📂 项目结构

```
ai-study-hub/
├── server.py              # Main server
├── storage.py             # Chat history storage
├── dictionary.py          # Dictionary features
├── vocabulary.py          # Vocabulary notebook
├── reading.py             # Reading practice
├── static/                # Frontend files
├── docs/                  # Documentation
├── scripts/               # Utility scripts
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables example
└── config.yml.example    # Configuration file example
```

### ⚙️ 配置说明

#### 环境变量 (.env)

```bash
# 应用密码（必须修改）
APP_PASSWORD=your_secure_password

# Relay API 配置（可选）
RELAY_API_KEY=your_api_key
RELAY_BASE_URL=https://api.example.com/v1
```

#### API 配置 (config.yml)

```yaml
relay:
  default_provider: default
  providers:
    default:
      base_url: https://api.example.com/v1
      api_key: your_api_key_here
      models:
        - gpt-4
        - gpt-3.5-turbo
      api_type: chat_completions
```

### 🔒 安全建议

1. **修改默认密码** - 在 `.env` 中设置强密码
2. **保护配置文件** - 不要提交 `.env` 和 `config.yml`
3. **使用 HTTPS** - 通过 Cloudflare Tunnel 或反向代理
4. **定期备份** - 备份 `chats/` 目录和数据库

### 📖 文档

- [管理器使用指南](docs/管理器使用指南.md)
- [管理面板使用指南](docs/管理面板使用指南.md)
- [功能配置指南](docs/功能配置指南.md)
- [AI生成文章完整指南](docs/AI生成文章完整指南.md)

### 🤝 贡献

欢迎贡献！请查看 [CONTRIBUTING.md](CONTRIBUTING.md)

### 📄 许可证

[MIT License](LICENSE)

### 🙏 致谢

- [ECDICT](https://github.com/skywind3000/ECDICT) - 免费英汉词典
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Web 框架
- [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk) - AI 集成支持

---

## English

A full-featured AI chat and learning platform with mobile and desktop access, including intelligent conversation, English learning and reading comprehension features.

### ✨ Features

- 🤖 **Multi-Model Support** - Support for various AI models (Claude, GPT, etc.)
- 💬 **Chat Features** - Full conversation history, image upload, PDF support
- 📚 **English Learning** - ECDICT dictionary, vocabulary notebook, statistics
- 📖 **Reading Practice** - CET-6 reading comprehension, AI-generated articles
- 📱 **Multi-Platform** - Desktop, mobile, and remote access
- 🛠️ **Management Tools** - CLI manager + Web admin panel

### 🚀 Quick Start

#### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2. Configure Environment

```bash
# Copy configuration files
cp .env.example .env
cp config.yml.example config.yml

# Edit .env to set password
# APP_PASSWORD=your_secure_password
```

#### 3. Dictionary Database
# Dictionary database is already included. In learning mode, double-click to translate words.

#### 4. Start Server

**Windows:**
```bash
# Using manager (recommended)
admin_pannel.bat

# Or start directly
start.bat
```

**Linux/Mac:**
```bash
python server.py
```

#### 5. Access Application

- **Chat Interface**: http://localhost:8000
- **Admin Panel**: http://localhost:8000/admin.html
- **Default Password**: `change-me-please` (please change)

### 📱 Mobile Access

#### Same WiFi
1. Get computer IP: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
2. Access from phone: `http://your-ip:8000`

#### Remote Access (Cloudflare Tunnel)
1. Download [cloudflared](https://github.com/cloudflare/cloudflared/releases)
2. Run: `cloudflared tunnel --url http://localhost:8000`
3. Use generated URL

### 🤝 Contributing

Contributions welcome! See [CONTRIBUTING.md](CONTRIBUTING.md)

### 📄 License

[MIT License](LICENSE)

---

**Last Updated**: 2024-05-31
