# chatgptmail-2api

> ⚡ 逆向解析多个临时邮箱平台的 Web API 协议，提供统一 Python 客户端 + HTTP API 服务。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-69%20passing-brightgreen.svg)](#运行测试)
[![Providers](https://img.shields.io/badge/Providers-10-orange.svg)](#支持平台)

## 支持平台

| Provider | API Base | 认证方式 | 特点 | 状态 |
|----------|----------|----------|------|------|
| [ChatGPTMail](https://mail.chatgpt.org.uk) | `mail.chatgpt.org.uk` | 首页 Token | TLS 指纹 | ✅ |
| [TempMail.ing](https://tempmail.ing) | `api.tempmail.ing` | 无 | ETag 缓存 | ✅ |
| [Boomlify](https://boomlify.com) | `v1.boomlify.com` | 公开 API | XOR 加密 | ✅ |
| [GuerrillaMail](https://guerrillamail.com) | `api.guerrillamail.com` | Session | 老牌服务 | ✅ |
| [Mail.tm](https://mail.tm) | `api.mail.tm` | JWT Token | 邮件删除 | ✅ |
| [Emailnator](https://emailnator.com) | Web 逆向 | 无 | Gmail dot trick | ✅ |
| [Mohmal](https://mohmal.com) | Web 逆向 | Session | 45 分钟有效 | ✅ |
| [Yopmail](https://yopmail.com) | Web 逆向 | 无需注册 | 长期有效 | ✅ |
| [Temp-Mail.org](https://temp-mail.org) | `web2.temp-mail.org` | Token | 逆向自网站 | ✅ |
| [TempMail.lol](https://tempmail.lol) | `api.tempmail.lol/v2` | 无 (可选 Key) | 免费 | ✅ |

## 快速开始

### 1. 安装依赖

```bash
pip install curl_cffi requests beautifulsoup4
```

或使用 pyproject.toml:

```bash
pip install -e .
```

### 2. Python 客户端

```python
from providers import TempMailIngClient, MailTmClient, YopmailClient

# 任选一个 provider
client = MailTmClient()

# 生成临时邮箱
email = client.generate_email()
print(f"邮箱地址: {email.address}")

# 查看收件箱
emails = client.list_emails(email.address)
for e in emails:
    print(f"  [{e.subject}] from {e.from_email}")
```

### 3. CLI 命令行

```bash
# 生成邮箱
python cli.py generate tempmail
python cli.py generate mailtm
python cli.py generate guerrillamail
python cli.py generate mohmal
python cli.py generate yopmail
python cli.py generate tempmail.lol

# 查看收件箱（自动识别 provider）
python cli.py inbox user@domain.com

# 等待邮件
python cli.py wait user@domain.com --timeout 120
```

### 4. HTTP API 服务

```bash
python server.py                    # 默认 127.0.0.1:8787
python server.py --port 9090        # 指定端口
```

**API 端点:**

```bash
# 健康检查
curl http://localhost:8787/api/health

# 生成邮箱（支持所有 10 个 provider）
curl -X POST http://localhost:8787/api/generate \
  -H "Content-Type: application/json" \
  -d '{"provider": "mailtm"}'

# 查看收件箱
curl "http://localhost:8787/api/inbox?address=user@domain.com"

# 列出所有 provider
curl http://localhost:8787/api/providers
```

### 5. 端到端测试

```bash
python examples/demo_all.py              # 测试所有平台
python examples/demo_all.py tempmail     # 仅测试 tempmail.ing
python examples/demo_all.py mailtm       # 仅测试 mail.tm
```

## 项目结构

```
├── providers/
│   ├── __init__.py          # 统一导出（10 个 provider）
│   ├── base.py              # 抽象基类 + 数据模型
│   ├── utils.py             # 重试、缓存等工具
│   ├── chatgptmail.py       # mail.chatgpt.org.uk
│   ├── tempmail_ing.py      # tempmail.ing
│   ├── boomlify.py          # boomlify.com (XOR 解密)
│   ├── guerrillamail.py     # guerrillamail.com
│   ├── mail_tm.py           # mail.tm (JWT)
│   ├── emailnator.py        # emailnator.com (Gmail dot trick)
│   ├── mohmal.py            # mohmal.com (curl_cffi)
│   ├── yopmail.py           # yopmail.com (BeautifulSoup)
│   ├── tempmail_org.py      # temp-mail.org (token)
│   └── tempmail_lol.py      # tempmail.lol (REST)
├── tests/
│   ├── test_providers.py    # Provider 单元测试
│   ├── test_providers_mock.py # 模拟测试
│   └── test_server.py       # API 服务集成测试
├── cli.py                   # CLI 工具
├── server.py                # HTTP API 服务（69 个测试）
├── pyproject.toml
├── Dockerfile
├── docker-compose.yml
└── API NOTES*.md            # 协议逆向文档
```

## 核心机制

*   **统一接口**: 所有 provider 实现 `TempMailClient` 抽象基类
*   **TLS 指纹伪装**: `curl_cffi` 模拟 Chrome TLS 指纹绕过 Cloudflare
*   **XOR 解密**: Boomlify 响应使用 XOR 加密
*   **JWT 认证**: Mail.tm 使用无状态 JWT Token
*   **BeautifulSoup 解析**: Yopmail/Mohmal HTML 解析
*   **指数退避重试**: 通用重试装饰器
*   **速率限制**: 滑动窗口 60 req/min per IP

## 运行测试

```bash
pip install -e ".[dev]"
python -m pytest tests/ -v           # 69 个测试
```

## Docker 部署

```bash
docker compose up -d
# 或
docker build -t chatgptmail-2api .
docker run -p 8787:8787 chatgptmail-2api
```

## 免责声明

本代码仅供协议研究与端到端测试学习使用。请遵循各目标站点的使用规范，勿用于恶意消耗公共资源或发送垃圾邮件。

## License

[MIT](LICENSE)
