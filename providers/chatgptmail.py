"""
ChatGPTMail provider
API: https://mail.chatgpt.org.uk
无需认证，通过首页提取 token，使用 curl_cffi 模拟 Chrome 指纹
"""

import json
import logging
import re
from typing import Any, Dict, List, Optional

from curl_cffi import requests as curl_requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("chatgptmail-2api")

BASE_URL = "https://mail.chatgpt.org.uk"


class ChatGPTMailClient(TempMailClient):
    def __init__(self) -> None:
        self.session = curl_requests.Session(impersonate="chrome136")
        self._initial_token: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "chatgptmail"

    def _get_initial_token(self) -> str:
        """从首页提取 window.__BROWSER_AUTH.token"""
        if self._initial_token:
            return self._initial_token

        response = self.session.get(BASE_URL, timeout=15)
        response.raise_for_status()

        match = re.search(r"window\.__BROWSER_AUTH\s*=\s*({[^}]+})", response.text)
        if not match:
            raise EmailGenerateError("未能从首页提取 window.__BROWSER_AUTH")

        auth_data = json.loads(match.group(1))
        token = auth_data.get("token")
        if not token:
            raise EmailGenerateError("首页鉴权数据中不存在 token")

        self._initial_token = token
        return token

    @retry(max_attempts=3, backoff_factor=2.0, exceptions=(Exception,))
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        initial_token = self._get_initial_token()

        headers = {
            "X-Inbox-Token": initial_token,
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {}
        if domain:
            payload["domain"] = domain

        try:
            response = self.session.post(
                f"{BASE_URL}/api/generate-email",
                headers=headers,
                json=payload,
                timeout=15,
            )
            response.raise_for_status()
        except Exception as e:
            raise EmailGenerateError(f"chatgptmail 生成邮箱失败: {e}") from e

        data = response.json()
        if not data.get("success"):
            raise EmailGenerateError(f"chatgptmail 返回失败: {data}")

        email = data.get("data", {}).get("email")
        inbox_token = data.get("auth", {}).get("token")

        if not email or not inbox_token:
            raise EmailGenerateError(f"返回结果缺少字段: {data}")

        self._inbox_token = inbox_token
        logger.info("chatgptmail 生成邮箱: %s", email)
        return TempEmail(
            address=email,
            provider=self.provider_name,
            raw=data,
        )

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(Exception,))
    def list_emails(self, address: str) -> List[InboxEmail]:
        if not hasattr(self, "_inbox_token"):
            raise EmailFetchError("请先调用 generate_email()")

        headers = {"X-Inbox-Token": self._inbox_token}
        try:
            response = self.session.get(
                f"{BASE_URL}/api/emails",
                params={"email": address},
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
        except Exception as e:
            raise EmailFetchError(f"chatgptmail 获取收件箱失败: {e}") from e

        data = response.json()
        emails = data.get("data", {}).get("emails", [])
        return [
            InboxEmail(
                id=str(e.get("id", "")),
                provider=self.provider_name,
                subject=e.get("subject"),
                from_email=e.get("from"),
                body_html=e.get("body"),
                received_at=e.get("date"),
                raw=e,
            )
            for e in emails
        ]

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(Exception,))
    def get_email_detail(self, email_id: str) -> InboxEmail:
        if not hasattr(self, "_inbox_token"):
            raise EmailFetchError("请先调用 generate_email()")

        headers = {"X-Inbox-Token": self._inbox_token}
        try:
            response = self.session.get(
                f"{BASE_URL}/api/email/{email_id}",
                headers=headers,
                timeout=15,
            )
            response.raise_for_status()
        except Exception as e:
            raise EmailFetchError(f"chatgptmail 获取邮件详情失败: {e}") from e

        data = response.json()
        email_data = data.get("data", {})
        return InboxEmail(
            id=str(email_data.get("id", email_id)),
            provider=self.provider_name,
            subject=email_data.get("subject"),
            from_email=email_data.get("from"),
            body_html=email_data.get("body"),
            body_text=email_data.get("text"),
            received_at=email_data.get("date"),
            raw=data,
        )
