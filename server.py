#!/usr/bin/env python3
"""
临时邮箱 HTTP API 服务 — 4 个经实测验证的 provider
基于 http.server，无需额外依赖

启动:
    python server.py                    # 默认 8787 端口
    python server.py --port 9090        # 指定端口
    python server.py --host 0.0.0.0     # 允许外部访问

端点:
    GET  /api/health                 健康检查
    POST /api/generate               生成临时邮箱
    GET  /api/inbox?address=xxx      查看收件箱
    GET  /api/inbox?address=xxx&id=xxx  查看邮件详情
    GET  /api/providers              列出支持的 provider
"""

import argparse
import json
import logging
import time
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Any, Dict
from urllib.parse import urlparse, parse_qs

from providers.inboxkitten import InboxkittenClient as InboxKittenClient
from providers.mailnesia import MailnesiaClient
from providers.anonymmail import AnonymmailClient
from providers.tempmail_lol import TempMailLolClient
from providers.chatgptmail import ChatGPTMailClient
from providers.tempmail_ing import TempMailIngClient
from providers.emailtick import EmailTickClient

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("api-server")

PROVIDERS = {
    "inboxkitten": InboxKittenClient,
    "mailnesia": MailnesiaClient,
    "anonymmail": AnonymmailClient,
    "tempmaillol": TempMailLolClient,
    "tempmail.lol": TempMailLolClient,
    "chatgptmail": ChatGPTMailClient,
    "tempmail": TempMailIngClient,
    "tempmailing": TempMailIngClient,
    "emailtick": EmailTickClient,
    "mailticking": EmailTickClient,
}

DEFAULT_PROVIDER = "inboxkitten"
START_TIME = time.time()


class RateLimiter:
    """简单的内存速率限制器（滑动窗口）"""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window = window_seconds
        self._requests: Dict[str, list] = {}

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        if key not in self._requests:
            self._requests[key] = []
        self._requests[key] = [t for t in self._requests[key] if now - t < self.window]
        if len(self._requests[key]) >= self.max_requests:
            return False
        self._requests[key].append(now)
        return True


rate_limiter = RateLimiter(max_requests=60, window_seconds=60)


def json_response(handler: BaseHTTPRequestHandler, status: int, data: Any) -> None:
    """发送 JSON 响应"""
    body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.end_headers()
    handler.wfile.write(body)


def get_client(provider_name: str = DEFAULT_PROVIDER):
    """获取 provider 客户端"""
    cls = PROVIDERS.get(provider_name)
    if not cls:
        return None
    return cls()


class APIHandler(BaseHTTPRequestHandler):
    def _check_rate_limit(self) -> bool:
        client_ip = self.client_address[0]
        if not rate_limiter.is_allowed(client_ip):
            json_response(self, 429, {
                "error": "请求过于频繁，请稍后再试",
                "retry_after_seconds": rate_limiter.window,
            })
            return False
        return True

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if not self._check_rate_limit():
            return
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        if path == "/api/health":
            self._handle_health()
        elif path == "/api/docs":
            self._handle_openapi()
        elif path == "/api/providers":
            self._handle_providers()
        elif path == "/api/inbox":
            self._handle_inbox(params)
        elif path == "/":
            json_response(self, 200, {
                "service": "chatgptmail-2api",
                "version": "2.3.0",
                "description": "多个经实测验证的临时邮箱 provider",
                "providers": list(PROVIDERS.keys()),
                "endpoints": [
                    "GET /api/health",
                    "GET /api/docs (OpenAPI)",
                    "POST /api/generate",
                    "GET /api/inbox?address=xxx",
                    "GET /api/providers",
                ],
            })
        else:
            json_response(self, 404, {"error": "Not found"})

    def do_POST(self):
        if not self._check_rate_limit():
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/generate":
            self._handle_generate()
        else:
            json_response(self, 404, {"error": "Not found"})

    def _handle_health(self):
        uptime = time.time() - START_TIME
        json_response(self, 200, {
            "status": "ok",
            "uptime_seconds": round(uptime, 1),
            "providers": list(PROVIDERS.keys()),
        })

    def _handle_openapi(self):
        spec = {
            "openapi": "3.0.3",
            "info": {
                "title": "chatgptmail-2api",
                "version": "2.3.0",
                "description": "多个经实测验证的临时邮箱 provider (InboxKitten, Mailnesia, Anonymmail, TempMail.lol, ChatGPTMail, TempMail.ing, EmailTick)",
            },
            "paths": {
                "/api/health": {
                    "get": {"summary": "健康检查", "responses": {"200": {"description": "服务状态"}}}
                },
                "/api/generate": {
                    "post": {
                        "summary": "生成临时邮箱",
                        "requestBody": {
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "provider": {"type": "string", "enum": list(PROVIDERS.keys()), "default": DEFAULT_PROVIDER},
                                        }
                                    }
                                }
                            }
                        },
                        "responses": {"200": {"description": "生成的邮箱信息"}}
                    }
                },
                "/api/inbox": {
                    "get": {
                        "summary": "查看收件箱",
                        "parameters": [
                            {"name": "address", "in": "query", "required": True, "schema": {"type": "string"}},
                            {"name": "provider", "in": "query", "schema": {"type": "string"}},
                            {"name": "id", "in": "query", "schema": {"type": "string"}},
                        ],
                        "responses": {"200": {"description": "邮件列表或详情"}}
                    }
                },
                "/api/providers": {
                    "get": {"summary": "列出支持的 provider", "responses": {"200": {"description": "provider 列表"}}}
                },
            }
        }
        json_response(self, 200, spec)

    def _handle_providers(self):
        json_response(self, 200, {
            "providers": list(PROVIDERS.keys()),
            "default": DEFAULT_PROVIDER,
            "verified": ["inboxkitten", "mailnesia", "anonymmail", "tempmaillol", "chatgptmail", "tempmail", "emailtick"],
        })

    def _handle_generate(self):
        try:
            content_length = int(self.headers.get("Content-Length", 0))
            body = {}
            if content_length > 0:
                raw = self.rfile.read(content_length)
                body = json.loads(raw)

            provider = body.get("provider", DEFAULT_PROVIDER)
            client = get_client(provider)
            if not client:
                json_response(self, 400, {"error": f"未知 provider: {provider}，可选: {list(PROVIDERS.keys())}"})
                return

            email = client.generate_email()
            json_response(self, 200, {
                "address": email.address,
                "provider": email.provider,
                "created_at": email.created_at,
            })
        except Exception as e:
            logger.exception("生成邮箱失败")
            json_response(self, 500, {"error": str(e)})

    def _handle_inbox(self, params):
        try:
            address = params.get("address", [None])[0]
            if not address:
                json_response(self, 400, {"error": "缺少 address 参数"})
                return

            provider = params.get("provider", [DEFAULT_PROVIDER])[0]
            email_id = params.get("id", [None])[0]

            client = get_client(provider)
            if not client:
                json_response(self, 400, {"error": f"未知 provider: {provider}"})
                return

            if email_id:
                detail = client.get_email_detail(address, email_id)
                json_response(self, 200, {
                    "id": detail.id,
                    "subject": detail.subject,
                    "from_address": detail.from_email,
                    "from_name": detail.from_name,
                    "body_html": detail.body_html,
                    "body_text": detail.body_text,
                    "date": detail.received_at,
                    "provider": detail.provider,
                })
            else:
                emails = client.list_emails(address)
                json_response(self, 200, {
                    "address": address,
                    "provider": client.provider_name,
                    "count": len(emails),
                    "emails": [
                        {
                            "id": e.id,
                            "subject": e.subject,
                            "from_address": e.from_email,
                            "from_name": e.from_name,
                            "date": e.received_at,
                        }
                        for e in emails
                    ],
                })
        except Exception as e:
            logger.exception("查看收件箱失败")
            json_response(self, 500, {"error": str(e)})

    def log_message(self, format, *args):
        logger.info(format % args)


def main():
    parser = argparse.ArgumentParser(description="临时邮箱 HTTP API 服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8787, help="监听端口")
    args = parser.parse_args()

    server = HTTPServer((args.host, args.port), APIHandler)
    logger.info("🚀 API 服务启动: http://%s:%d", args.host, args.port)
    logger.info("📋 Provider: inboxkitten, mailnesia, anonymmail, tempmaillol, chatgptmail, tempmail, emailtick")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("服务停止")
        server.server_close()


if __name__ == "__main__":
    main()
