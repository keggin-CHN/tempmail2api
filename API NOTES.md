# AI 复刻说明：ChatGPTMail + Resend 端到端验证脚本

## 1. 这份文档的用途

这份文档是写给后续 AI 的，不是普通 README。

目标只有一个：让 AI 在没有原始脚本的情况下，也能复刻出与当前项目行为一致的 Python 脚本。

复刻目标文件应命名为：

`demo.py`

该脚本的职责不是封装 SDK，不是做库化设计，也不是做完整 CLI，而是完成一次**真实的端到端验证**：

1. 访问 `mail.chatgpt.org.uk` 首页
2. 从 HTML 中提取 `window.__BROWSER_AUTH`
3. 取出初始化 `token`
4. 调用 `/api/generate-email` 生成临时邮箱
5. 拿到邮箱专属 `auth.token`
6. 用 Resend HTTP API 向这个临时邮箱发送一封测试邮件
7. 轮询 `/api/emails?email=...`
8. 按主题关键字找到目标邮件
9. 再调用 `/api/email/{id}` 拉取详情
10. 打印完整结果并结束

---

## 2. 必须复刻出的整体结构

AI 生成的代码必须保持“一个脚本文件 + 一个客户端类 + 若干辅助函数 + 一个 `main()` 入口”的结构。

推荐严格按下面的组织方式复刻：

- 常量区
- `ChatGPTMailClient` 类
- `send_test_email_via_resend_api()`
- `extract_email_list()`
- `find_target_email()`
- `poll_for_email()`
- `main()`
- `if __name__ == "__main__": main()`

不要改造成异步版本，不要改造成类库，不要拆成多个文件。

---

## 3. 依赖约束

必须使用以下依赖组合：

- `requests`
- `curl_cffi.requests`
- Python 标准库中的：
  - `json`
  - `re`
  - `time`
  - `typing`

其中分工必须保持一致：

- `curl_cffi.requests.Session(impersonate="chrome136")` 用于访问 ChatGPTMail
- 普通 `requests.post(...)` 用于调用 Resend HTTP API

不能把 ChatGPTMail 那部分改成普通 `requests.Session()`，因为当前实现明确依赖浏览器指纹伪装。

---

## 4. 常量区必须包含的内容

顶部必须定义下面这些常量：

- `CHATGPTMAIL_BASE_URL = "https://mail.chatgpt.org.uk"`
- `RESEND_API_BASE_URL = "https://api.resend.com"`
- `RESEND_API_KEY`
- `SENDER_EMAIL`
- `SMTP_SERVER = "smtp.resend.com"`
- `SMTP_PORT = 465`
- `SMTP_USERNAME = "resend"`
- `POLL_INTERVAL_SECONDS = 5`
- `POLL_TIMEOUT_SECONDS = 120`

说明：

- SMTP 配置只是作为记录保留
- 当前脚本默认走 Resend HTTP API，不走 SMTP 发信

---

## 5. `ChatGPTMailClient` 的精确职责

这个类只负责与 ChatGPTMail 交互，不负责 Resend 发信。

它必须包含以下 4 个方法：

### `__init__()`

要点：

- 创建 `self.session = curl_requests.Session(impersonate="chrome136")`

### `get_initial_token() -> str`

行为要求：

1. `GET https://mail.chatgpt.org.uk`
2. 对返回 HTML 做正则提取：
   `window\.__BROWSER_AUTH\s*=\s*({[^}]+})`
3. `json.loads()` 解析这个对象
4. 返回其中的 `token`
5. 如果正则没有匹配到，抛出 `RuntimeError`
6. 如果对象里没有 `token`，也抛出 `RuntimeError`

### `generate_email(domain: Optional[str] = None) -> Tuple[str, str, Dict[str, Any]]`

行为要求：

1. 先调用 `get_initial_token()`
2. 用请求头：
   - `X-Inbox-Token: <initial_token>`
   - `Content-Type: application/json`
3. `POST https://mail.chatgpt.org.uk/api/generate-email`
4. `json={}` 作为默认请求体
5. 如果传入 `domain`，则把它放进 payload
6. 解析 JSON 返回
7. 要求 `success == True`
8. 从返回里取：
   - `data.email`
   - `auth.token`
9. 返回 `(email, inbox_token, raw_response_json)`
10. 缺字段时抛 `RuntimeError`

### `list_emails(email: str, inbox_token: str) -> Dict[str, Any]`

行为要求：

1. `GET https://mail.chatgpt.org.uk/api/emails`
2. Query 参数为 `email=<邮箱地址>`
3. 请求头包含 `X-Inbox-Token`
4. 直接返回 `response.json()`

### `get_email_detail(email_id: str, inbox_token: str) -> Dict[str, Any]`

行为要求：

1. `GET https://mail.chatgpt.org.uk/api/email/{email_id}`
2. 请求头包含 `X-Inbox-Token`
3. 直接返回 `response.json()`

---

## 6. Resend 发信函数的精确职责

需要有一个独立函数：

`send_test_email_via_resend_api(api_key, from_email, to_email, subject, html, text)`

它必须：

1. `POST https://api.resend.com/emails`
2. 请求头：
   - `Authorization: Bearer <api_key>`
   - `Content-Type: application/json`
3. 请求体字段：
   - `from`
   - `to`，并且是列表格式，如 `[to_email]`
   - `subject`
   - `html`
   - `text`
4. 使用 `requests.post(..., timeout=30)`
5. 尽量先 `response.json()`
6. 如果 JSON 解析失败，则返回 `{"raw_text": response.text}` 风格的兜底信息
7. 当 `status_code >= 400` 时抛出 `RuntimeError`

---

## 7. 收件箱辅助函数必须保留

需要保留三个小函数，职责不要合并：

### `extract_email_list(inbox_data)`

- 从 `inbox_data.get("data", {}).get("emails", [])` 取列表
- 如果不是列表，返回空列表

### `find_target_email(emails, subject_keyword)`

- 遍历邮件列表
- 取每一项的 `subject`
- 只要 `subject_keyword in subject` 就返回该邮件
- 否则返回 `None`

### `poll_for_email(client, email, inbox_token, subject_keyword, timeout_seconds=..., interval_seconds=...)`

行为要求：

1. 用 `deadline = time.time() + timeout_seconds` 控制超时
2. 循环调用 `client.list_emails(...)`
3. 每次轮询后先调用 `extract_email_list()`
4. 再调用 `find_target_email()`
5. 找到目标邮件就立刻返回
6. 未找到则打印当前轮询状态
7. `time.sleep(interval_seconds)` 后继续
8. 超时则抛出 `TimeoutError`
9. 超时报错里要带上最后一次收件箱结果，方便调试

---

## 8. `main()` 必须完成的真实流程

`main()` 不是示例函数，而是整个脚本的真实执行入口，必须顺序完成以下步骤：

1. 打印开始信息
2. 打印 SMTP 记录信息
3. 说明“默认使用 Resend HTTP API，而不是 SMTP”
4. 创建 `ChatGPTMailClient()`
5. 调用 `generate_email()`
6. 打印生成出的邮箱、Inbox Token、原始返回 JSON
7. 构造一个唯一主题关键字：
   `CHATGPTMAIL-TEST-<当前时间戳>`
8. 构造 text 正文与 html 正文
9. 调用 Resend 发信
10. 打印发信成功结果
11. 调用 `poll_for_email(...)`
12. 打印命中的目标邮件
13. 如果目标邮件包含 `id`，则再调用 `get_email_detail()`
14. 打印邮件详情
15. 最后打印“发信与收信链路正常”

这里的核心原则是：必须做真实调用，不要改成伪造数据或 mock 数据。

---

## 9. 输出风格也应尽量保持一致

为了让复刻结果与当前脚本尽量一致，建议保留下面这种打印风格：

- `=== ChatGPTMail + Resend 测试开始 ===`
- `[成功] 生成临时邮箱: ...`
- `[成功] Inbox Token: ...`
- `[调试] 生成邮箱原始返回: ...`
- `[成功] Resend 发信成功: ...`
- `[轮询] 暂未找到目标邮件，当前邮件数: ...`
- `[成功] 收到目标邮件: ...`
- `[成功] 邮件详情: ...`
- `=== 测试完成：发信与收信链路正常 ===`

---

## 10. 复刻时不要擅自优化掉的细节

后续 AI 在重写代码时，不要自作主张做下面这些“优化”：

- 不要改成异步
- 不要拆模块
- 不要改成类库
- 不要删除 SMTP 记录常量
- 不要把 `find_target_email()` 合并进 `poll_for_email()`
- 不要跳过 `get_email_detail()`
- 不要把 `curl_cffi` 换成普通 `requests`
- 不要把主题关键字改成固定值
- 不要去掉轮询日志
- 不要把异常吞掉

---

## 11. 面向 GitHub 的额外说明

当前原始脚本里包含演示用配置值。

如果 AI 是为了“公开发布到 GitHub”而重写脚本，允许做一项额外改动：

- 将 `RESEND_API_KEY`
- `SENDER_EMAIL`

改为从环境变量读取或改成占位符字符串。

但除此之外，脚本结构、函数划分、调用顺序、日志风格和异常处理都应尽量保持一致。

---

## 12. 一句话复刻标准

如果一个 AI 读完这份文档后，能重新写出一个单文件 Python 脚本，并且它能够：

- 先从首页提取 `window.__BROWSER_AUTH.token`
- 再生成临时邮箱
- 再用 Resend 发信
- 再轮询收件箱找到目标主题邮件
- 再按 `id` 拉取单封详情
- 最后输出与当前脚本近似的日志

那就说明复刻成功。
