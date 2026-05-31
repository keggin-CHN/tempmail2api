"""Segamail.com provider — simple REST API."""

from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class SegamailClient(TempMailClient):
    """Client for https://segamail.com/"""

    @property
    def provider_name(self) -> str:
        return "segamail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._recover_key = ""

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        resp = self._session.post("https://segamail.com/en/getEmailAddress", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            self._recover_key = data.get("recover_key", "")
            address = data.get("address", "")
            if address:
                return TempEmail(address=address, provider="segamail")
        raise TempMailError(f"Failed to create email: {resp.status_code}")

    def list_emails(self, address: str) -> list:
        resp = self._session.post("https://segamail.com/en/getInbox", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            result = []
            for i, m in enumerate(data):
                result.append(InboxEmail(
                    id=str(len(data) - i),
                    provider="segamail",
                    from_email=m.get("from", "unknown"),
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("date", "")),
                    body_text=m.get("body", ""),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        emails = self.list_emails(address)
        for e in emails:
            if e.id == email_id:
                return e
        return None
