"""Adguard.com tempmail provider — simple REST API."""

from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class AdguardClient(TempMailClient):
    """Client for https://tempmail.adguard.com/"""

    BASE_URL = "https://tempmail.adguard.com/"

    @property
    def provider_name(self) -> str:
        return "adguard"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        resp = self._session.post(self.BASE_URL, timeout=self._timeout)
        if resp.status_code == 200:
            text = resp.text
            if "copyEmailAddress('" in text:
                email = text.split("copyEmailAddress('", 1)[1].split("'", 1)[0]
                return TempEmail(address=email, provider="adguard")
        raise TempMailError(f"Failed to create email: {resp.status_code}")

    def list_emails(self, address: str) -> list:
        resp = self._session.get(f"{self.BASE_URL}messages?since_message_id=0", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            result = []
            for m in data.get("emails", []):
                result.append(InboxEmail(
                    id=str(m.get("message_id", "")),
                    provider="adguard",
                    from_email=m.get("from", [{}])[0].get("address", "unknown") if m.get("from") else "unknown",
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("time_added_timestamp", "")),
                    body_html=m.get("content_html", ""),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        emails = self.list_emails(address)
        for e in emails:
            if e.id == email_id:
                return e
        return None
