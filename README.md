# chatgptmail-2api

📧 临时邮箱聚合 API — 6 个经实测验证的 provider，提供统一的 OpenAI 兼容 API。

## ✅ 经实测验证的 Provider

| Provider | 网站 | 类型 | 验证状态 |
|----------|------|------|----------|
| **ChatGPTMail** | mail.chatgpt.org.uk | REST API | 项目基础 provider |
| **TempMail.ing** | tempmail.ing | REST API | 项目基础 provider |
| **InboxKitten** | inboxkitten.com | REST API | ✅ 多次收信成功 |
| **Mailnesia** | mailnesia.com | HTML 解析 | ✅ 多次收信成功 |
| **Anonymmail** | anonymmail.net | HTML 解析 | ✅ 收信成功 |
| **TempMail.lol** | tempmail.lol | REST API | ✅ 收信成功 |

> 所有 provider 均通过 WayinVideo 验证码收信测试，确认可真实接收邮件。

## 快速开始

```bash
# 安装
pip install -r requirements.txt

# 启动 API 服务
python server.py

# 生成临时邮箱
curl -X POST http://localhost:8787/api/generate \
  -H "Content-Type: application/json" \
  -d '{"provider": "inboxkitten"}'

# 查看收件箱
curl "http://localhost:8787/api/inbox?address=xxx@inboxkitten.com&provider=inboxkitten"

# 查看所有 provider
curl http://localhost:8787/api/providers
```

## CLI 使用

```bash
# 生成邮箱
python cli.py generate --provider inboxkitten

# 查看收件箱
python cli.py inbox --address xxx@inboxkitten.com --provider inboxkitten

# 列出 provider
python cli.py providers
```

## API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/health` | 健康检查 |
| GET | `/api/docs` | OpenAPI 文档 |
| POST | `/api/generate` | 生成临时邮箱 |
| GET | `/api/inbox?address=xxx` | 查看收件箱 |
| GET | `/api/inbox?address=xxx&id=xxx` | 查看邮件详情 |
| GET | `/api/providers` | 列出支持的 provider |

## 测试

```bash
python -m pytest tests/ -v
```

## 技术栈

- Python 3.10+
- `requests` + `beautifulsoup4` (HTML 解析)
- `curl_cffi` (TLS 指纹模拟，绕过 Cloudflare)

## License

MIT
