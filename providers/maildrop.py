"""Maildrop.cc provider — GraphQL API (api.maildrop.cc/graphql)."""

import logging
import random
import string
from typing import Optional, List

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailGenerateError, EmailFetchError

logger = logging.getLogger("chatgptmail-2api")

MAILDROP_DOMAIN = "maildrop.cc"


class MaildropClient(TempMailClient):
    """Client for Maildrop GraphQL API.

    Maildrop API 文档: https://docs.maildrop.cc/
    - 无需认证
    - GraphQL POST 到 https://api.maildrop.cc/graphql
    - 只读 inbox，不能发邮件
    - mailbox 24h 无活动自动清理，最多 10 封
    """

    BASE_URL = "https://api.maildrop.cc/graphql"

    @property
    def provider_name(self) -> str:
        return "maildrop"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    def _graphql(self, query: str, variables: Optional[dict] = None) -> dict:
        """Execute a GraphQL query."""
        payload = {"query": query}
        if variables:
            payload["variables"] = variables
        resp = self._session.post(self.BASE_URL, json=payload, timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
        if "errors" in data:
            raise TempMailError(f"GraphQL errors: {data['errors']}")
        return data.get("data", {})

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """Generate a random Maildrop address.

        Maildrop 不需要创建邮箱，任何 @maildrop.cc 地址都可以直接接收邮件。
        """
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        address = f"{name}@{MAILDROP_DOMAIN}"
        logger.info("maildrop 生成邮箱: %s", address)
        return TempEmail(address=address, provider="maildrop")

    def list_emails(self, address: str) -> List[InboxEmail]:
        """List emails in the Maildrop mailbox."""
        mailbox = address.split("@")[0]
        data = self._graphql(
            'query { inbox(mailbox: "%s") { id subject date headerfrom } }' % mailbox
        )
        emails = data.get("inbox", [])
        result = []
        for m in emails:
            result.append(InboxEmail(
                id=m.get("id", ""),
                provider="maildrop",
                subject=m.get("subject", ""),
                from_email=m.get("headerfrom", ""),
                received_at=m.get("date", ""),
            ))
        return result

    def get_email_detail(self, email_id: str) -> Optional[InboxEmail]:
        """Fetch full email content."""
        # 需要知道 mailbox name，从最近的 address 获取
        # 这里通过 list_emails 的缓存或上下文获取
        # Maildrop API 需要 mailbox + id 两个参数
        # 为了简单，这里使用一个通用查询
        # 注意：这需要知道 mailbox name，所以我们需要保存它
        if not hasattr(self, '_last_mailbox'):
            return None

        data = self._graphql(
            'query { message(mailbox: "%s", id: "%s") { id subject date headerfrom data html } }'
            % (self._last_mailbox, email_id)
        )
        msg = data.get("message")
        if not msg:
            return None
        return InboxEmail(
            id=msg.get("id", email_id),
            provider="maildrop",
            subject=msg.get("subject", ""),
            from_email=msg.get("headerfrom", ""),
            body_html=msg.get("html", ""),
            body_text=msg.get("data", ""),
            received_at=msg.get("date", ""),
        )

    def list_emails(self, address: str) -> List[InboxEmail]:
        """List emails in the Maildrop mailbox."""
        mailbox = address.split("@")[0]
        self._last_mailbox = mailbox  # 保存以便 get_email_detail 使用
        data = self._graphql(
            'query { inbox(mailbox: "%s") { id subject date headerfrom } }' % mailbox
        )
        emails = data.get("inbox", [])
        result = []
        for m in emails:
            result.append(InboxEmail(
                id=m.get("id", ""),
                provider="maildrop",
                subject=m.get("subject", ""),
                from_email=m.get("headerfrom", ""),
                received_at=m.get("date", ""),
            ))
        return result

    def delete_email(self, email_id: str) -> bool:
        """Delete an email from Maildrop."""
        if not hasattr(self, '_last_mailbox'):
            return False
        try:
            self._graphql(
                'mutation { delete(mailbox: "%s", id: "%s") }'
                % (self._last_mailbox, email_id)
            )
            return True
        except Exception:
            return False
