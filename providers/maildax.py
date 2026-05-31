"""Maildax.com provider — simple REST API."""

from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class MaildaxClient(TempMailClient):
    """Client for https://maildax.com/"""

    BASE_URL = "https://api2.maildax.com"

    @property
    def provider_name(self) -> str:
        return "maildax"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._email = ""
        self._secret = ""

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        resp = self._session.post(f"{self.BASE_URL}/api/email", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            self._email = data.get("email", "")
            self._secret = data.get("secret", "")
            if self._email:
                return TempEmail(address=self._email, provider="maildax")
        raise TempMailError(f"Failed to create email: {resp.status_code}")

    def list_emails(self, address: str) -> list:
        resp = self._session.get(
            f"{self.BASE_URL}/api/email/mails",
            params={"email": address, "secret": self._secret},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            result = []
            for m in data.get("data", []):
                result.append(InboxEmail(
                    id=str(m.get("_id", "")),
                    provider="maildax",
                    from_email=m.get("from", "unknown"),
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("date", "")),
                    body_text=m.get("text", ""),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        resp = self._session.get(
            f"{self.BASE_URL}/api/email/mail/{email_id}",
            params={"secret": self._secret},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json().get("data", {})
            return InboxEmail(
                id=email_id,
                provider="maildax",
                from_email=data.get("from", "unknown"),
                subject=data.get("subject", "(no subject)"),
                received_at=str(data.get("date", "")),
                body_html=data.get("html", ""),
                body_text=data.get("text", ""),
            )
        return None
