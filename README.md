# chatgptmail-2api

> ⚡ 逆向解析多个临时邮箱平台的 Web API 协议，提供统一 Python 客户端实现。

## 支持平台

| 平台 | API Base | 认证方式 | 加密 | 状态 |
|------|----------|----------|------|------|
| [mail.chatgpt.org.uk](https://mail.chatgpt.org.uk) | 同左 | 首页 Token | ❌ | ✅ |
| [tempmail.ing](https://tempmail.ing) | `api.tempmail.ing` | 无 | ❌ | ✅ |
| [boomlify.com](https://boomlify.com) | `v1.boomlify.com` | Guest JWT | ✅ XOR | ✅ |

## 核心机制

*   **统一接口**: 所有 provider 实现 `TempMailClient` 抽象基类，提供一致的 `generate_email()` / `list_emails()` / `get_email_detail()` API。
*   **TLS 指纹伪装**: ChatGPTMail 通过 `curl_cffi` 模拟 Chrome 指纹绕过风控。
*   **Token 劫持**: ChatGPTMail 从首页 `window.__BROWSER_AUTH` 提取鉴权 Token。
*   **XOR 解密**: Boomlify 响应使用 XOR 加密，密钥从前端 JS 提取。
*   **ETag 缓存**: TempMail.ing 支持 ETag 条件请求，减少重复数据传输。

## 快速开始

### 1. 安装依赖

```bash
pip install curl_cffi requests
```

### 2. 使用统一客户端

```python
from providers import TempMailIngClient, BoomlifyClient, ChatGPTMailClient

# 任选一个 provider
client = TempMailIngClient()

# 生成临时邮箱
email = client.generate_email(duration_minutes=10)
print(f"邮箱地址: {email.address}")

# 查看收件箱
emails = client.list_emails(email.address)
print(f"当前邮件数: {len(emails)}")

# 获取邮件详情
if emails:
    detail = client.get_email_detail(emails[0].id)
    print(f"主题: {detail.subject}")
```

### 3. 运行端到端测试

```bash
# 测试所有平台
python examples/demo_all.py

# 测试单个平台
python examples/demo_all.py tempmail
python examples/demo_all.py boomlify
python examples/demo_all.py chatgptmail
```

## 项目结构

```
├── providers/
│   ├── __init__.py          # 统一导出
│   ├── base.py              # 抽象基类 + 数据模型
│   ├── chatgptmail.py       # mail.chatgpt.org.uk 客户端
│   ├── tempmail_ing.py      # tempmail.ing 客户端
│   └── boomlify.py          # boomlify.com 客户端
├── examples/
│   └── demo_all.py          # 多平台端到端测试
├── demo.py                  # 原始 ChatGPTMail 测试脚本
├── API NOTES.md             # ChatGPTMail 协议文档
├── API_NOTES_TEMPMAIL_ING.md
└── API_NOTES_BOOMLIFY.md
```

## 协议文档

每个平台的逆向协议细节:

- [`API NOTES.md`](./API%20NOTES.md) — ChatGPTMail 协议
- [`API_NOTES_TEMPMAIL_ING.md`](./API_NOTES_TEMPMAIL_ING.md) — TempMail.ing 协议
- [`API_NOTES_BOOMLIFY.md`](./API_NOTES_BOOMLIFY.md) — Boomlify 协议

## 免责声明

本代码仅供协议研究与端到端测试学习使用。请遵循各目标站点的使用规范，勿用于恶意消耗公共资源或发送垃圾邮件。
