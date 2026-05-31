# 贡献指南

感谢你对本项目的关注！我们欢迎各种形式的贡献。

## 如何贡献

### 报告问题

如果你发现了 bug 或有功能建议：

1. 先搜索现有的 Issues，避免重复
2. 创建新 Issue，清晰描述问题或建议
3. 提供复现步骤（如果是 bug）
4. 附上相关的日志或截图

### 提交代码

1. **Fork 本仓库**
2. **创建特性分支**
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **编写代码**
   - 遵循现有代码风格
   - 添加必要的注释
   - 确保代码可以正常运行
4. **提交更改**
   ```bash
   git commit -m "feat: 添加某某功能"
   ```
5. **推送到你的 Fork**
   ```bash
   git push origin feature/your-feature-name
   ```
6. **创建 Pull Request**
   - 清晰描述你的更改
   - 关联相关的 Issue

## 代码规范

### Python 代码风格

- 遵循 PEP 8 规范
- 使用 4 个空格缩进
- 函数和类添加文档字符串
- 变量命名使用小写加下划线

### 提交信息规范

使用语义化的提交信息：

- `feat:` 新功能
- `fix:` 修复 bug
- `docs:` 文档更新
- `style:` 代码格式调整
- `refactor:` 代码重构
- `test:` 测试相关
- `chore:` 构建/工具相关

示例：
```
feat: 添加单词发音功能
fix: 修复手机端图片上传问题
docs: 更新安装说明
```

## 开发环境设置

1. **克隆仓库**
   ```bash
   git clone https://github.com/your-username/ai-study-hub.git
   cd ai-study-hub
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置环境**
   ```bash
   cp .env.example .env
   cp config.yml.example config.yml
   # 编辑配置文件
   ```

4. **运行服务**
   ```bash
   python server.py
   ```

## 测试

在提交 PR 前，请确保：

- [ ] 代码可以正常运行
- [ ] 没有引入新的错误
- [ ] 核心功能正常工作
- [ ] 文档已更新（如果需要）

## 需要帮助？

如果你在贡献过程中遇到问题：

- 查看项目文档
- 在 Issue 中提问
- 联系维护者

再次感谢你的贡献！🎉
