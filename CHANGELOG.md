# Changelog

## v2.3.0 (2026-05-31)

### 新增 Provider (总计 10 个)
- **Mail.tm** (api.mail.tm): 免费 REST API，JWT 认证，邮件删除
- **Emailnator** (emailnator.com): Gmail dot trick 临时邮箱
- **Mohmal** (mohmal.com): 45 分钟有效期，curl_cffi 绕过 Cloudflare
- **Yopmail** (yopmail.com): 老牌临时邮箱，BeautifulSoup HTML 解析
- **Temp-Mail.org** (web2.temp-mail.org): 逆向自网站 REST API
- **TempMail.lol** (api.tempmail.lol/v2): 免费 REST API，无需 Key

### 改进
- 新增 beautifulsoup4 依赖
- 总测试数: 69 个全部通过
- README / CHANGELOG 全面更新

## v2.2.0 (2026-05-31)

### Features
- 新增速率限制中间件 (60 req/min per IP, 滑动窗口)
- 新增 `/api/health` 健康检查端点
- 新增 `/api/docs` OpenAPI 3.0 规范端点
- CLI 支持 GuerrillaMail provider
- 自动识别 GuerrillaMail 域名
- 启动日志显示可用端点

### Infrastructure
- 新增 `pyproject.toml` (现代 Python 项目配置)
- 新增 MIT LICENSE
- 重写 `.gitignore` (完整 Python 规则)
- GitHub Actions CI (Python 3.8/3.10/3.12)
- Dockerfile: 多阶段构建 + 非 root 用户 + HEALTHCHECK
- docker-compose.yml: 添加 healthcheck
- 新增 `Makefile` 常用开发命令

### Tests
- 新增 `test_providers_mock.py` (模拟测试各 provider 客户端)
- 新增 health/docs/CORS/GuerrillaMail 集成测试
- 总测试数: 47 个全部通过

### Documentation
- 更新 README.md: 新增 GuerrillaMail 支持、badge、完善文档
- 新增 CHANGELOG.md

## v2.1.0 (2026-05-30)

### Features
- 新增 GuerrillaMail provider (`providers/guerrillamail.py`)
- 统一异常体系 (`TempMailError`, `EmailGenerateError`, `EmailFetchError`, `RateLimitError`)
- ETag 缓存管理器 (`ETagCache`)
- 通用重试装饰器 (`retry`)
- 自适应轮询间隔 (前 30s 用 2s 间隔)

### Tests
- 单元测试: XOR 加解密、ETag 缓存、异常类、重试装饰器、数据模型
- API 集成测试: 服务端点全覆盖

## v2.0.0 (2026-05-20)

### Features
- 重构为 providers 包结构
- 抽象基类 `TempMailClient`
- 统一数据模型 `TempEmail`, `InboxEmail`
- 支持 3 个 provider: ChatGPTMail, TempMail.ing, Boomlify
- HTTP API 服务 (基于 http.server)
- CLI 命令行工具
- Docker 支持

### Documentation
- ChatGPTMail API 协议文档
- TempMail.ing API 协议文档
- Boomlify API 协议文档 (含 XOR 解密)
