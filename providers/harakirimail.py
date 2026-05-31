"""Harakirimail provider — simple REST API."""

import random
import string
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class HarakirimailClient(TempMailClient):
    """Client for https://harakirimail.com/"""

    BASE_URL = "https://harakirimail.com/api/v1"

    @property
    def provider_name(self) -> str:
        return "harakirimail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        })

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@harakirimail.com"
        return TempEmail(address=address, provider="harakirimail")

    def list_emails(self, address: str) -> list:
        name = address.split("@")[0]
        resp = self._session.get(f"{self.BASE_URL}/inbox/{name}", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            emails_data = data.get("emails", [])
            result = []
            for m in emails_data:
                result.append(InboxEmail(
                    id=str(m.get("_id", "")),
                    provider="harakirimail",
                    from_email=m.get("from", "unknown"),
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("received", "")),
                    body_text=m.get("text", ""),
                    body_html=m.get("bodyhtml", ""),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        resp = self._session.get(f"{self.BASE_URL}/email/{email_id}", timeout=self._timeout)
        if resp.status_code == 200:
            m = resp.json()
            return InboxEmail(
                id=str(m.get("_id", "")),
                provider="harakirimail",
                from_email=m.get("from", "unknown"),
                subject=m.get("subject", "(no subject)"),
                received_at=str(m.get("received", "")),
                body_text=m.get("text", ""),
                body_html=m.get("bodyhtml", ""),
            )
        return None
