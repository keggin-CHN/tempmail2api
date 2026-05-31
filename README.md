# chatgptmail-2api

> ⚡ 逆向解析多个临时邮箱平台的 Web API 协议，提供统一 Python 客户端 + HTTP API 服务。

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-passing-brightgreen.svg)](#端到端测试)

## 支持平台

| 平台 | API Base | 认证方式 | 加密 | 状态 |
|------|----------|----------|------|------|
| [mail.chatgpt.org.uk](https://mail.chatgpt.org.uk) | 同左 | 首页 Token | ❌ | ✅ |
| [tempmail.ing](https://tempmail.ing) | `api.tempmail.ing` | 无 | ❌ | ✅ |
| [boomlify.com](https://boomlify.com) | `v1.boomlify.com` | 公开 API | ✅ XOR | ✅ |
| [guerrillamail.com](https://guerrillamail.com) | `api.guerrillamail.com` | Session | ❌ | ✅ |

## 快速开始

### 1. 安装依赖

```bash
pip install curl_cffi requests
```

或使用 pyproject.toml:

```bash
pip install -e .
```

### 2. Python 客户端

```python
from providers import TempMailIngClient, BoomlifyClient, ChatGPTMailClient, GuerrillaMailClient

# 任选一个 provider
client = TempMailIngClient()

# 生成临时邮箱
email = client.generate_email(duration_minutes=10)
print(f"邮箱地址: {email.address}")

# 等待邮件（轮询）
received = client.wait_for_email(email.address, timeout=120)
if received:
    print(f"主题: {received.subject}")
```

### 3. CLI 命令行

```bash
# 生成邮箱
python cli.py generate tempmail
python cli.py generate boomlify
python cli.py generate chatgptmail
python cli.py generate guerrillamail

# 查看收件箱
python cli.py inbox user@domain.com

# 等待邮件
python cli.py wait user@domain.com --timeout 120

# 查看可用域名
python cli.py domains boomlify
```

### 4. HTTP API 服务

```bash
# 启动服务
python server.py                    # 默认 127.0.0.1:8787
python server.py --port 9090        # 指定端口
python server.py --host 0.0.0.0     # 允许外部访问
```

**API 端点:**

```bash
# 健康检查
curl http://localhost:8787/api/health

# 生成邮箱
curl -X POST http://localhost:8787/api/generate \
  -H "Content-Type: application/json" \
  -d '{"provider": "tempmail", "duration": 10}'

# 查看收件箱
curl "http://localhost:8787/api/inbox?address=user@domain.com"

# 查看邮件详情
curl "http://localhost:8787/api/inbox?address=user@domain.com&id=email_id"

# 查看可用域名
curl "http://localhost:8787/api/domains?provider=boomlify"

# 列出支持的 provider
curl "http://localhost:8787/api/providers"
```

### 5. 端到端测试

```bash
python examples/demo_all.py              # 测试所有平台
python examples/demo_all.py tempmail     # 仅测试 tempmail.ing
python examples/demo_all.py boomlify     # 仅测试 boomlify
python examples/demo_all.py chatgptmail  # 仅测试 chatgptmail
```

## 项目结构

```
├── providers/
│   ├── __init__.py          # 统一导出
│   ├── base.py              # 抽象基类 + 数据模型
│   ├── utils.py             # 重试、日志等工具
│   ├── chatgptmail.py       # mail.chatgpt.org.uk 客户端
│   ├── tempmail_ing.py      # tempmail.ing 客户端
│   ├── boomlify.py          # boomlify.com 客户端
│   └── guerrillamail.py     # guerrillamail.com 客户端
├── examples/
│   └── demo_all.py          # 多平台端到端测试
├── tests/
│   ├── test_providers.py    # Provider 单元测试
│   └── test_server.py       # API 服务集成测试
├── cli.py                   # CLI 命令行工具
├── server.py                # HTTP API 服务
├── demo.py                  # 原始 ChatGPTMail 测试脚本
├── pyproject.toml           # 项目配置
├── Dockerfile               # Docker 构建
├── docker-compose.yml       # Docker Compose
├── API NOTES.md             # ChatGPTMail 协议文档
├── API_NOTES_TEMPMAIL_ING.md
└── API_NOTES_BOOMLIFY.md
```

## 核心机制

*   **统一接口**: 所有 provider 实现 `TempMailClient` 抽象基类
*   **TLS 指纹伪装**: ChatGPTMail 通过 `curl_cffi` 模拟 Chrome 指纹
*   **XOR 解密**: Boomlify 响应使用 XOR 加密，密钥从前端 JS 提取
*   **ETag 缓存**: TempMail.ing 支持 ETag 条件请求
*   **指数退避重试**: 通用重试装饰器，支持自定义退避策略
*   **自适应轮询**: `wait_for_email` 前 30 秒使用较短间隔（2s），之后恢复常规间隔

## 运行测试

```bash
# 安装开发依赖
pip install -e ".[dev]"

# 运行所有测试
python -m pytest tests/ -v

# 运行测试并生成覆盖率报告
python -m pytest tests/ -v --cov=providers --cov-report=term-missing
```

## Docker 部署

```bash
# 使用 Docker Compose
docker compose up -d

# 或手动构建
docker build -t chatgptmail-2api .
docker run -p 8787:8787 chatgptmail-2api
```

## 协议文档

- [`API NOTES.md`](./API%20NOTES.md) — ChatGPTMail 协议
- [`API_NOTES_TEMPMAIL_ING.md`](./API_NOTES_TEMPMAIL_ING.md) — TempMail.ing 协议
- [`API_NOTES_BOOMLIFY.md`](./API_NOTES_BOOMLIFY.md) — Boomlify 协议

## 免责声明

本代码仅供协议研究与端到端测试学习使用。请遵循各目标站点的使用规范，勿用于恶意消耗公共资源或发送垃圾邮件。

## License

[MIT](LICENSE)
