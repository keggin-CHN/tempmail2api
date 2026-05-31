"""TemporaryMail.com — REST API (getDomains, requestEmailAccess, checkInbox)."""

import random
import string
from typing import List, Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailFetchError


class TemporarymailClient(TempMailClient):
    """Client for https://temporarymail.com/ (REST API)."""

    BASE_URL = "https://temporarymail.com/api"

    def __init__(self):
        self._session = requests.Session()
        self._address: Optional[str] = None
        self._secret_key: Optional[str] = None
        self._domains: Optional[List[str]] = None

    @property
    def provider_name(self) -> str:
        return "temporarymail.com"

    def _get_domains(self) -> List[str]:
        if self._domains:
            return self._domains

        resp = self._session.get(f"{self.BASE_URL}/?action=getDomains", timeout=15)
        resp.raise_for_status()
        self._domains = resp.json()
        return self._domains

    def generate_email(self) -> TempEmail:
        domains = self._get_domains()
        if not domains:
            raise TempMailError("无法获取域名列表")

        domain = random.choice(domains)
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@{domain}"

        resp = self._session.get(
            f"{self.BASE_URL}/?action=requestEmailAccess&value={address}",
            timeout=15,
        )
        resp.raise_for_status()

        data = resp.json()
        if data.get("code") == 403:
            raise TempMailError("邮箱已被使用")
        elif data.get("code") == 429:
            raise TempMailError("频率限制")

        self._address = data.get("address", address)
        self._secret_key = data.get("secretKey", "")

        if not self._address:
            raise TempMailError("创建邮箱失败")

        return TempEmail(address=self._address, provider="temporarymail.com")

    def list_emails(self, address: str) -> List[InboxEmail]:
        if not self._secret_key:
            raise TempMailError("需要先调用 generate_email")

        resp = self._session.get(
            f"{self.BASE_URL}/?action=checkInbox&value={self._secret_key}",
            timeout=15,
        )
        resp.raise_for_status()

        data = resp.json()
        result = []

        if isinstance(data, dict):
            for item in data.values():
                result.append(InboxEmail(
                    id=item.get("id", ""),
                    from_address=item.get("from", ""),
                    subject=item.get("subject", ""),
                    date=item.get("date", ""),
                    body_html="",
                    body_text="",
                    provider="temporarymail.com",
                    address=address or self._address or "",
                ))

        return result

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        if not self._secret_key:
            raise TempMailError("需要先调用 generate_email")

        # Get subject
        resp = self._session.get(
            f"{self.BASE_URL}/?action=getEmail&value={email_id}",
            timeout=15,
        )
        subject = ""
        sender = ""
        if resp.ok:
            try:
                data = resp.json()
                if email_id in data:
                    subject = data[email_id].get("subject", "")
                    sender = data[email_id].get("from", "")
            except Exception:
                pass

        # Get content
        resp2 = self._session.get(
            f"https://temporarymail.com/view/?i={email_id}",
            timeout=15,
        )
        body_html = resp2.text if resp2.ok else ""

        return InboxEmail(
            id=email_id,
            from_address=sender,
            subject=subject,
            date="",
            body_html=body_html,
            body_text="",
            provider="temporarymail.com",
            address=address or self._address or "",
        )
