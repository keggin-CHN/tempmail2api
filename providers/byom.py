"""Byom.de — simple REST API (api.byom.de)."""

import random
import string
from typing import List, Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailFetchError


class ByomClient(TempMailClient):
    """Client for https://byom.de/ (api.byom.de)."""

    DOMAIN = "byom.de"

    def __init__(self):
        self._session = requests.Session()
        self._name: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "byom.de"

    def generate_email(self) -> TempEmail:
        self._name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=random.randint(8, 14)))
        address = f"{self._name}@{self.DOMAIN}"
        return TempEmail(address=address, provider="byom.de")

    def list_emails(self, address: str) -> List[InboxEmail]:
        name = address.split("@")[0] if address else self._name
        if not name:
            raise TempMailError("需要邮箱地址")

        resp = self._session.get(f"https://api.byom.de/mails/{name}", timeout=15)
        resp.raise_for_status()

        data = resp.json()
        result = []
        for item in data:
            content = item.get("content", item.get("text", ""))
            result.append(InboxEmail(
                id=str(item.get("id", "")),
                from_address=item.get("from", ""),
                subject=item.get("subject", ""),
                date=item.get("created_at", ""),
                body_html=content,
                body_text=content,
                provider="byom.de",
                address=address,
            ))
        return result

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        name = address.split("@")[0] if address else self._name
        if not name:
            raise TempMailError("需要邮箱地址")

        resp = self._session.get(f"https://api.byom.de/mails/{name}", timeout=15)
        resp.raise_for_status()

        data = resp.json()
        for item in data:
            if str(item.get("id", "")) == email_id:
                content = item.get("content", item.get("text", ""))
                return InboxEmail(
                    id=email_id,
                    from_address=item.get("from", ""),
                    subject=item.get("subject", ""),
                    date=item.get("created_at", ""),
                    body_html=content,
                    body_text=content,
                    provider="byom.de",
                    address=address,
                )

        raise TempMailError(f"邮件 {email_id} 未找到")
