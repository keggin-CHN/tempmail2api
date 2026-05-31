"""ThrowawayMail.app — REST API (no auth required)."""

from typing import List, Optional
import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailFetchError


class ThrowawayMailClient(TempMailClient):
    """Client for https://throwawaymail.app/ (REST API)."""

    BASE_URL = "https://throwawaymail.app/api"

    def __init__(self):
        self._session = requests.Session()
        self._mailbox_id: Optional[str] = None
        self._address: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "throwawaymail.app"

    def generate_email(self) -> TempEmail:
        resp = self._session.post(f"{self.BASE_URL}/mailboxes", timeout=15)
        if resp.status_code not in [200, 201]:
            raise TempMailError(f"创建邮箱失败: {resp.status_code}")

        data = resp.json()
        self._mailbox_id = data.get("mailbox_id", "")
        self._address = data.get("address", "")

        if not self._address:
            raise TempMailError("创建邮箱失败: 无效响应")

        return TempEmail(address=self._address, provider="throwawaymail.app")

    def _get_mailbox_id(self, address: str) -> str:
        if self._mailbox_id and address == self._address:
            return self._mailbox_id
        raise TempMailError("需要先调用 generate_email 获取邮箱")

    def list_emails(self, address: str) -> List[InboxEmail]:
        mailbox_id = self._get_mailbox_id(address)

        resp = self._session.get(
            f"{self.BASE_URL}/mailboxes/{mailbox_id}/messages", timeout=15
        )
        resp.raise_for_status()

        data = resp.json()
        result = []
        for item in data:
            result.append(InboxEmail(
                id=item.get("message_id", ""),
                from_address=item.get("from_address", ""),
                subject=item.get("subject", ""),
                date=item.get("received_at", ""),
                body_html=item.get("snippet", ""),
                body_text=item.get("snippet", ""),
                provider="throwawaymail.app",
                address=address,
            ))
        return result

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        mailbox_id = self._get_mailbox_id(address)

        resp = self._session.get(
            f"{self.BASE_URL}/mailboxes/{mailbox_id}/messages/{email_id}",
            timeout=15,
        )
        resp.raise_for_status()

        data = resp.json()
        return InboxEmail(
            id=email_id,
            from_address=data.get("from_address", ""),
            subject=data.get("subject", ""),
            date=data.get("received_at", ""),
            body_html=data.get("html", ""),
            body_text=data.get("text", ""),
            provider="throwawaymail.app",
            address=address,
        )
