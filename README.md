# ChatGPTMail-2API

📧 临时邮箱聚合 API — 支持 72 个临时邮箱服务商，提供统一的 OpenAI 兼容 API。

## 特性

- **72 个 Provider** — 覆盖主流临时邮箱服务
- **统一 API** — OpenAI 兼容格式
- **浏览器模拟** — curl_cffi 绕过 Cloudflare
- **速率限制** — 60 req/min per IP
- **Docker 就绪** — 多阶段构建，非 root 运行
- **完整测试** — 146 测试用例
- **✅ 实测验证** — 多个 provider 通过 WayinVideo 验证码收信测试

## Provider 列表

| # | Provider | 网站 | 类型 |
|---|----------|------|------|
| 1 | ChatGPTMail | mail.chatgpt.org.uk | REST API |
| 2 | TempMail.ing | tempmail.ing | REST API |
| 3 | Boomlify | boomlify.com | REST API |
| 4 | GuerrillaMail | guerrillamail.com | REST API |
| 5 | Mail.tm | mail.tm | REST API (GraphQL) |
| 6 | Emailnator | emailnator.com | REST API + TLS |
| 7 | Mohmal | mohmal.com | HTML 解析 |
| 8 | TempMail.lol | tempmail.lol | REST API |
| 9 | Temp-Mail.org | temp-mail.org | REST API + Token |
| 10 | Yopmail | yopmail.com | HTML 解析 |
| 11 | Mail.gw | mail.gw | REST API (Mail.tm 兼容) |
| 12 | Harakirimail | harakirimail.com | REST API |
| 13 | Tempmail.plus | tempmail.plus | REST API |
| 14 | Inboxes.com | inboxes.com | REST API |
| 15 | Noopmail | noopmail.org | REST API |
| 16 | Mailnesia | mailnesia.com | HTML 解析 |
| 17 | Moakt | moakt.com | HTML 解析 |
| 18 | Fakemail.net | fakemail.net | Minuteinbox 模式 |
| 19 | Emailfake | emailfake.com | Generatoremail 模式 |
| 20 | Tempomail | tempomail.top | REST API + API Key |
| 21 | Anonymmail | anonymmail.net | REST API |
| 22 | EmailOnDeck | emailondeck.com | AJAX API |
| 23 | Etempmail | etempmail.com | REST API |
| 24 | Tempm | tempm.com | Generatoremail 模式 |
| 25 | Generator.email | generator.email | Generatoremail 模式 |
| 26 | Email-fake | email-fake.com | Generatoremail 模式 |
| 27 | Adguard | tempmail.adguard.com | REST API |
| 28 | InboxKitten | inboxkitten.com | REST API |
| 29 | Disposablemail | disposablemail.com | Minuteinbox 模式 |
| 30 | Fakemailgenerator | fakemailgenerator.com | HTML 解析 + WebSocket |
| 31 | Trashmail | trash-mail.com | HTML 解析 |
| 32 | 1SecMail | 1secmail.com | REST API |
| 33 | Maildax | maildax.com | REST API |
| 34 | Fakermail | fakermail.com | REST API |
| 35 | MintEmail | mintemail.com | REST API |
| 36 | Eztempmail | eztempmail.com | CSRF + REST API |
| 37 | Tmail.gg | tmail.gg | HTML 解析 |
| 38 | Tempemail.co | tempemail.co | REST API + HTML |
| 39 | Mailgolem | mailgolem.com | CSRF + REST API |
| 40 | Muellmail | muellmail.com | GraphQL API |
| 41 | Mailsac | mailsac.com | HTML 解析 + JSON |
| 42 | Tempmail.guru | tempmail.guru | REST API |
| 43 | Crazymailing | crazymailing.com | HTML 解析 |
| 44 | Eyepaste | eyepaste.com | REST API |
| 45 | Segamail | segamail.com | REST API |
| 46 | Tempmails.net | tempmails.net | CSRF + REST API |
| 47 | Tempmailso | tempmailso.com | Fake_trash_mail |
| 48 | Haribu | haribu.net | Tempail 模式 |
| 49 | Incognitomail | incognitomail.co | HMAC REST API |

### ✅ 实测验证（WayinVideo 验证码收信测试）

| Provider | 状态 | 备注 |
|----------|------|------|
| InboxKitten | ✅ 稳定 | 多次测试均成功 |
| Mailnesia | ✅ 稳定 | 多次测试均成功 |
| Anonymmail | ✅ 稳定 | 自动检测 HTML/纯文本 |
| TempMail.lol | ✅ 稳定 | list_emails 含完整内容 |

## 快速开始

### API 接口

```bash
# 创建邮箱
curl -X POST http://localhost:8787/api/generate \
  -H "Content-Type: application/json" \
  -d '{"provider": "1secmail"}'

# 查看收件箱
curl "http://localhost:8787/api/inbox?address=xxx@1secmail.com&provider=1secmail"

# 查看邮件详情
curl "http://localhost:8787/api/email/{email_id}?address=xxx@1secmail.com&provider=1secmail"

# 查看所有 provider
curl http://localhost:8787/api/providers

# 健康检查
curl http://localhost:8787/api/health
```

### CLI 使用

```bash
python -m cli generate --provider 1secmail
python -m cli inbox --address test@1secmail.com --provider 1secmail
python -m cli providers
```

## 开发

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Docker

```bash
docker build -t chatgptmail-2api .
docker run -p 8787:8787 chatgptmail-2api
```

## License

MIT
