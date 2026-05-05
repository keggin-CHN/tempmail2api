# chatgptmail-2api

> ⚡ 逆向解析 `mail.chatgpt.org.uk` 内部接口，提供自动化收发验证的端到端纯净实现。

## 简介

本项目包含一个极简的 Python 验证脚本（`demo.py`），通过抹平 TLS 指纹差异，绕过 `mail.chatgpt.org.uk` 的前置风控。
无需真实的浏览器环境，即可实现**极速生成临时邮箱**、**自动化轮询收件**、**邮件详情拉取**的完整生命周期管理。

## 核心机制

*   **TLS 指纹伪装**: 结合 `curl_cffi` 模拟 Chrome 136 指纹，稳定通过前端校验。
*   **Token 劫持**: 正则嗅探首页 `window.__BROWSER_AUTH` 状态，动态无缝签发后续 API 所需的 `X-Inbox-Token`。
*   **E2E 闭环验证**: 内置 Resend HTTP API 对接。从发信、轮询到收件解析，一键跑通真实链路。
*   **轻量化交付**: 拒绝过度设计与臃肿封装，核心协议逻辑单文件梭哈，方便降维移植。

## 快速开始

### 1. 环境准备

环境要求：Python 3.8+。

```bash
pip install curl_cffi requests
```

### 2. 参数配置

编辑 `demo.py`，配置用于端到端测试的发信凭证：

```python
RESEND_API_KEY = "re_..."            # 你的 Resend API Key
SENDER_EMAIL = "test@yourdomain.com" # 你的发件地址
```

### 3. 运行链路

```bash
python demo.py
```

执行后，脚本将自动串联走完以下流程：
取首页 Token -> 签发临时邮箱 -> 触发 Resend 投递特征测试邮件 -> 轮询查收 -> 提取邮件 ID 及完整 RAW 数据。

## 协议白皮书

逆向还原的协议细节及其复刻约束，已归档于 [`API NOTES.md`](./API%20NOTES.md)。
如遇接口变更，或需要将其重构至 Go/Node.js 等其他技术栈，请以此备忘录为准。

## 免责声明

本代码仅供协议研究与端到端测试学习使用。请遵循目标站点的使用规范，勿用于恶意消耗公共资源或发送垃圾邮件。
