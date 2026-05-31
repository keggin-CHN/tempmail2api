"""
Temp-Mail.org provider
API: https://web2.temp-mail.org
逆向自 temp-mail.org 网站，无需 API Key
文档参考: https://github.com/Zai-Kun/reverse-engineered-temp-mail-API
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("chatgptmail-2api")

API_BASE = "https://web2.temp-mail.org"
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36"


class TempMailOrgClient(TempMailClient):
    """Temp-Mail.org 客户端 — 逆向自网站 Web API"""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": USER_AGENT,
            "Accept": "application/json, text/plain, */*",
        })
        self._token: Optional[str] = None
        self._address: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "temp-mail.org"

    @retry(max_attempts=3, backoff_factor=1.5, exceptions=(requests.RequestException,))
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """创建临时邮箱（随机生成）"""
        try:
            r = self.session.post(f"{API_BASE}/mailbox", timeout=15)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            raise EmailGenerateError(f"temp-mail.org 创建邮箱失败: {e}") from e
        except Exception as e:
            raise EmailGenerateError(f"temp-mail.org 响应解析失败: {e}") from e

        self._address = data.get("mailbox", "")
        self._token = data.get("token", "")

        if not self._address or not self._token:
            raise EmailGenerateError(f"temp-mail.org 创建邮箱返回数据不完整: {data}")

        logger.info("temp-mail.org 生成邮箱: %s", self._address)
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

        headers = {"Authorization": self._token}
        try:
            r = self.session.get(f"{API_BASE}/messages", headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            raise EmailFetchError(f"temp-mail.org 获取收件箱失败: {e}") from e

        messages = data.get("messages", [])
        return [
            InboxEmail(
                id=str(m.get("_id", "")),
                provider=self.provider_name,
                subject=m.get("subject"),
                from_email=m.get("from"),
                body_text=m.get("bodyPreview"),
                received_at=m.get("receivedAt"),
                raw=m,
            )
            for m in messages
        ]

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(requests.RequestException,))
    def get_email_detail(self, email_id: str) -> InboxEmail:
        """获取邮件详情"""
        if not self._token:
            raise EmailFetchError("请先调用 generate_email()")

        headers = {"Authorization": self._token}
        try:
            r = self.session.get(f"{API_BASE}/messages/{email_id}", headers=headers, timeout=15)
            r.raise_for_status()
            data = r.json()
        except requests.RequestException as e:
            raise EmailFetchError(f"temp-mail.org 获取邮件详情失败: {e}") from e

        return InboxEmail(
            id=str(data.get("_id", email_id)),
            provider=self.provider_name,
            subject=data.get("subject"),
            from_email=data.get("from"),
            body_html=data.get("bodyHtml"),
            body_text=data.get("textBody") or data.get("bodyPreview"),
            received_at=data.get("receivedAt"),
            raw=data,
        )
