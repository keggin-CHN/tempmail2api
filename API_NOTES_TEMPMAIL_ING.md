# TempMail.ing API 协议文档

> 最后验证: 2026-05-30

## 概述

`tempmail.ing` 使用 Cloudflare Worker 作为后端 API，无需认证即可使用。
前端为传统 JS + HTML 渲染（非 SPA），API 返回 JSON。

## 基础信息

- **API Base**: `https://api.tempmail.ing`
- **认证**: 无需
- **TLS 指纹**: 普通 requests 即可，不需要 curl_cffi
- **限流**: 有速率限制，建议间隔 10 秒以上

## 端点

### 1. 生成邮箱

```
POST /api/generate
Content-Type: application/json

{
  "duration": 10  // 可选: 5, 10, 15, 20, 30, 60 (分钟)
}
```

**响应**:
```json
{
  "email": {
    "address": "abc123@randomdomain.com",
    "expiresAt": "2026-05-30T08:05:23.151Z",
    "createdAt": "2026-05-30T07:55:23.481Z",
    "durationMinutes": 10
  },
  "success": true
}
```

### 2. 获取收件箱

```
GET /api/emails/{emailAddress}
```

注意: `emailAddress` 需要 URL 编码（`@` → `%40`）。

**响应**:
```json
{
  "emails": [
    {
      "id": "...",
      "subject": "...",
      "from": "sender@example.com",
      "html": "<html>...</html>",
      "text": "...",
      "createdAt": "2026-05-30T07:56:00.000Z"
    }
  ],
  "success": true
}
```

**ETag 支持**: 响应包含 `ETag` 头，后续请求可用 `If-None-Match` 条件查询，304 表示无变化。

### 3. 获取邮件详情

```
GET /api/emails/{emailId}
```

### 4. 删除邮件

```
DELETE /api/emails/{emailId}
```

## 注意事项

- 域名随机分配，不可选择
- 邮箱过期后自动删除所有关联邮件
- 支持 ETag 缓存减少不必要的数据传输
- 前端 JS 文件: `/app.js?v=20260505`
- API base 在 JS 中硬编码: `this.apiBase = 'https://api.tempmail.ing'`
