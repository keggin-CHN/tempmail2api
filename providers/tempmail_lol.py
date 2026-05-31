"""
TempMail.lol provider
API: https://api.tempmail.lol/v2
免费公开 REST API，无需 API Key
支持 Plus/Ultra 付费 API Key（可选）
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("chatgptmail-2api")

API_BASE = "https://api.tempmail.lol/v2"


class TempMailLolClient(TempMailClient):
    """TempMail.lol 客户端 — 免费公开 REST API"""

    def __init__(self, api_key: Optional[str] = None) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "chatgptmail-2api/2.2.0",
            "Accept": "application/json",
        })
        self._api_key = api_key
        self._token: Optional[str] = None
        self._address: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "tempmail.lol"

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """发送 API 请求"""
        headers = {}
        if self._api_key:
            headers["Authorization"] = f"Bearer {self._api_key}"

        r = self.session.request(
            method, f"{API_BASE}{path}", headers=headers, timeout=15, **kwargs
        )

        if r.status_code == 429:
            raise EmailGenerateError("tempmail.lol 速率限制，请稍后重试")
        r.raise_for_status()
        return r.json()

    @retry(max_attempts=3, backoff_factor=1.5, exceptions=(requests.RequestException,))
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """创建临时邮箱"""
        payload: Dict[str, Any] = {}
        if domain:
            payload["domain"] = domain

        try:
            data = self._request("POST", "/inbox/create", json=payload)
        except requests.RequestException as e:
            raise EmailGenerateError(f"tempmail.lol 创建邮箱失败: {e}") from e

        self._address = data.get("address", "")
        self._token = data.get("token", "")

        if not self._address or not self._token:
            raise EmailGenerateError(f"tempmail.lol 创建邮箱返回数据不完整: {data}")

        logger.info("tempmail.lol 生成邮箱: %s", self._address)
        return TempEmail(
            address=self._address,
            provider=self.provider_name,
            raw=data,
        )

    @retry(max_attempts=3, backoff_factor=1.0, exceptions=(requests.RequestException,))
    def list_emails(self, address: str) -> List[InboxEmail]:
        """获取收件箱列表"""
        if not self._token:
            raise EmailFetchError("请先调用 generate_email()")

        try:
            data = self._request("GET", f"/inbox?token={self._token}")
        except requests.RequestException as e:
            raise EmailFetchError(f"tempmail.lol 获取收件箱失败: {e}") from e

        if data.get("expired"):
            raise EmailFetchError("token 已过期，请重新生成邮箱")

        messages = data.get("emails") or []
        return [
            InboxEmail(
                id=str(i),
                provider=self.provider_name,
                subject=m.get("subject"),
                from_email=m.get("from"),
                body_text=m.get("body"),
                body_html=m.get("html"),
                received_at=str(m.get("date")) if m.get("date") else None,
                raw=m,
            )
            for i, m in enumerate(messages)
        ]

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        """获取邮件详情（list_emails 已包含完整内容）"""
        # list_emails already returns full content, just find by index
        emails = self.list_emails(self._address or address or "")
        idx = int(email_id) if email_id.isdigit() else 0
        if 0 <= idx < len(emails):
            return emails[idx]
        raise EmailFetchError(f"邮件 {email_id} 不存在")
