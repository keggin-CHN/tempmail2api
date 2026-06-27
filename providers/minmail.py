"""
MinMail provider
API: https://minmail.app/api
免费 REST API，无需 API Key
邮箱有效期默认 24 小时
"""

import logging
import uuid
from typing import Any, Dict, List, Optional

import requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("minmail")

API_BASE = "https://minmail.app/api"


class MinMailClient(TempMailClient):
    """MinMail 客户端 — 免费 REST API"""

    @property
    def provider_name(self) -> str:
        return "minmail"

    def __init__(self) -> None:
        self.session = requests.Session()
        self._visitor_id = str(uuid.uuid4())
        self._address: Optional[str] = None
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://minmail.app/",
            "visitor-id": self._visitor_id,
        })

    @retry(max_attempts=2)
    def generate_email(self, duration_minutes: int = 1440, domain: Optional[str] = None) -> TempEmail:
        """生成临时邮箱地址"""
        params = {
            "refresh": "true",
            "expire": str(duration_minutes),
            "part": "main",
        }
        resp = self.session.get(f"{API_BASE}/mail/address", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        address = data.get("address", "")
        if not address:
            raise EmailGenerateError(f"MinMail API 返回空地址: {data}")

        self._address = address
        logger.info("Generated MinMail email: %s", address)

        return TempEmail(
            address=address,
            provider="minmail",
            expires_at=str(data.get("expire", "")),
            raw=data,
        )

    @retry(max_attempts=2, backoff_factor=2)
    def list_emails(self, address: str) -> List[InboxEmail]:
        """获取收件箱"""
        params = {
            "address": address,
            "page": "1",
            "limit": "50",
            "part": "main",
        }
        resp = self.session.get(f"{API_BASE}/mail/list", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        messages = data.get("message", [])
        if not isinstance(messages, list):
            return []

        emails = []
        for msg in messages:
            emails.append(InboxEmail(
                id=str(msg.get("id", "")),
                provider="minmail",
                from_email=msg.get("from", ""),
                subject=msg.get("subject", ""),
                received_at=msg.get("date", ""),
                body_text=msg.get("content", ""),
                body_html=msg.get("content", ""),
                raw=msg,
            ))
        return emails

    @retry(max_attempts=2)
    def get_email_detail(self, email_id: str) -> InboxEmail:
        """获取邮件详情（MinMail 列表已包含内容，先尝试从列表中查找）"""
        if not self._address:
            raise EmailFetchError("请先调用 generate_email()")

        emails = self.list_emails(self._address)
        for e in emails:
            if e.id == email_id:
                return e
        raise EmailFetchError(f"邮件 {email_id} 未找到")
