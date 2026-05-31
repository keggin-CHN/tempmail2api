"""Etempmail.com provider — simple REST API."""

import random
import string
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class EtempmailClient(TempMailClient):
    """Client for https://etempmail.com/"""

    BASE_URL = "https://etempmail.com"

    @property
    def provider_name(self) -> str:
        return "etempmail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        resp = self._session.post(f"{self.BASE_URL}/getEmailAddress", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            address = data.get("address", "")
            if address:
                return TempEmail(address=address, provider="etempmail")
        raise TempMailError(f"Failed to create email: {resp.status_code}")

    def list_emails(self, address: str) -> list:
        resp = self._session.post(f"{self.BASE_URL}/getInbox", timeout=self._timeout)
        if resp.status_code == 200:
            try:
                emails = resp.json()
            except Exception:
                return []
            result = []
            for m in emails:
                result.append(InboxEmail(
                    id=str(m.get("id", hash(m.get("subject", "")))),
                    provider="etempmail",
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
