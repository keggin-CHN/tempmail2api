"""InboxKitten.com provider — simple REST API."""

import random
import string
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class InboxkittenClient(TempMailClient):
    """Client for https://inboxkitten.com/"""

    BASE_URL = "https://inboxkitten.com"

    @property
    def provider_name(self) -> str:
        return "inboxkitten"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@inboxkitten.com"
        return TempEmail(address=address, provider="inboxkitten")

    def list_emails(self, address: str) -> list:
        name = address.split("@")[0]
        resp = self._session.get(
            f"{self.BASE_URL}/api/v1/mail/list",
            params={"recipient": name},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            result = []
            for m in resp.json():
                headers = m.get("message", {}).get("headers", {})
                storage = m.get("storage", {})
                result.append(InboxEmail(
                    id=f"{storage.get('region', '')},{storage.get('key', '')}",
                    provider="inboxkitten",
                    from_email=headers.get("from", "unknown"),
                    subject=headers.get("subject", "(no subject)"),
                    received_at=str(m.get("timestamp", "")),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        if "," not in email_id:
            return None
        region, key = email_id.split(",", 1)
        resp = self._session.get(
            f"{self.BASE_URL}/api/v1/mail/getHtml",
            params={"region": region, "key": key},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            html = resp.text.rsplit("<script>", 1)[0] if "<script>" in resp.text else resp.text
            return InboxEmail(
                id=email_id,
                provider="inboxkitten",
                body_html=html,
            )
        return None
