# Boomlify.com API 协议文档

> 最后验证: 2026-05-30

## 概述

`boomlify.com` 是一个功能丰富的临时邮箱平台，采用 React SPA 前端 + Express/Node.js 后端。
API 基础 URL 为 `https://v1.boomlify.com`，所有 `/api/v1/*` 端点需要 API Key，
访客通过 `/guest/*` 端点免认证使用。

**关键特性**: 所有响应经过 XOR 加密，前端在收到后解密。

## 基础信息

- **API Base**: `https://v1.boomlify.com`
- **前端**: `https://boomlify.com` (React + Vite)
- **认证**: Guest session (JWT) 或 API Key (`X-API-Key`)
- **加密**: XOR 加密，密钥硬编码在前端 JS 中
- **CORS**: 允许跨域

## 加密机制

### 密钥

前端 `main.CfEsQkv6.js` 中提取:

```
encryptionKey.keyString = "7a9b3c8d2e1f4g5h6i9j0k8l2m4n6o8p"
```

### 解密流程

1. 响应体如果是 `{"encrypted": "<hex_string>"}` 格式，需要解密
2. 将密钥转为 UTF-8 字节: `key_bytes = key.encode("utf-8")`
3. 将 hex 字符串转为字节: `encrypted_bytes = bytes.fromhex(hex_string)`
4. 逐字节 XOR: `decrypted[i] = encrypted_bytes[i] ^ key_bytes[i % len(key_bytes)]`
5. 将结果 UTF-8 解码并 JSON 解析

### Transport Key Ring

部分端点返回时带有 `X-Enc-Key-Id` 响应头，需要用对应的备用密钥解密:
```json
{
  "hgjfh": "rk4kA9fQm8v7W4d2TzX1Y",
  "hgjfhg": "t2PzKd9sQw1Lm3X..."
}
```

## 端点

### 1. 初始化访客会话

```
POST /guest/init
Content-Type: application/json

{}
```

**响应** (解密后):
```json
{
  "token": "eyJhbGciOiJIUzI1NiIs...",
  "user": {
    "id": "guest_xxx",
    "isGuest": true
  }
}
```

JWT token 用于后续请求的 `Authorization: Bearer <token>` 头。

### 2. 创建临时邮箱 (访客)

```
POST /guest/emails/create
Authorization: Bearer <guest_token>
Content-Type: application/json

{
  "domain_id": "可选的域名ID"
}
```

**响应** (解密后):
```json
{
  "email": {
    "id": "...",
    "address": "random@domain.com",
    "domain_id": "...",
    "expires_at": "2026-08-30T...",
    "created_at": "2026-05-30T...",
    "_sig": "..."
  }
}
```

### 3. 获取收件箱 (访客)

```
GET /guest/emails/{emailAddress}
Authorization: Bearer <guest_token>
```

### 4. 获取邮件详情 (访客)

```
GET /guest/emails/{emailId}
Authorization: Bearer <guest_token>
```

### 5. 获取公共域名列表

```
GET /domains/public
```

### 6. 认证用户端点 (需要 API Key)

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/v1/generate` | POST | 生成邮箱 |
| `/api/v1/inbox` | GET | 收件箱 |
| `/api/v1/domains` | GET | 域名列表 |
| `/api/v1/me` | GET | 当前用户信息 |
| `/api/v1/auth` | GET | 认证信息 |
| `/api/v1/auth/guest` | POST | 创建访客 |
| `/api/v1/session` | GET | 会话信息 |
| `/api/v1/email` | GET | 邮件 |
| `/api/v1/emails` | GET | 邮件列表 |

所有 `/api/v1/*` 端点需在请求头中带 `X-API-Key: <key>` 或查询参数 `api_key=<key>`。

## 前端关键模块

| 文件 | 职责 |
|------|------|
| `main.CfEsQkv6.js` | 加密/解密、axios 拦截器、全局状态管理 |
| `ui.BmXKn17L.js` | 图标库、公共 UI 组件 |
| `features.DfzegTxi.js` | 功能模块路由和特性声明 |
| `GuestDashboard.DobUO8JJ.js` | 访客控制台页面 |
| `Dashboard.n6PGKwDQ.js` | 用户控制台页面 |
| `guestSessionCache.DVaUR75U.js` | 访客会话本地缓存 |
| `utils.D4cqkT9n.js` | Axios 实例、通用工具函数 |

## 注意事项

- 访客会话有 JWT 过期时间，过期后需要重新 init
- 加密密钥可能随版本更新变化
- 前端使用 localStorage 缓存 guest emails (`boomlify_guest_tempemail_*`)
- Smart Inbox Preview 是其特色功能，支持同时监控多个邮箱
- 免费用户有广告，Premium 用户可通过 `ads_allowed=false` 关闭
- 支持自定义域名（Pro 功能）
