"""Anonymmail.net provider — simple REST API."""

import random
import string
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class AnonymmailClient(TempMailClient):
    """Client for https://anonymmail.net/"""

    BASE_URL = "https://anonymmail.net"

    @property
    def provider_name(self) -> str:
        return "anonymmail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.head(self.BASE_URL, timeout=self._timeout)
        self._session.headers.update({
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
        })

    def _get_domains(self) -> list:
        resp = self._session.post(f"{self.BASE_URL}/api/getDomains", data=None, timeout=self._timeout)
        if resp.status_code == 200:
            return [d["domain"] for d in resp.json()]
        return []

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        if not domains:
            raise TempMailError("No domains available")
        selected = domain if domain and domain in domains else domains[0]
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@{selected}"
        resp = self._session.post(f"{self.BASE_URL}/api/create", data={"email": address}, timeout=self._timeout)
        if resp.status_code == 200 and resp.json().get("success"):
            return TempEmail(address=address, provider="anonymmail")
        raise TempMailError(f"Failed to create email: {resp.text}")

    def list_emails(self, address: str) -> list:
        resp = self._session.post(f"{self.BASE_URL}/api/get", data={"email": address}, timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            emails_data = data.get(address, {}).get("emails", [])
            result = []
            for m in emails_data:
                result.append(InboxEmail(
                    id=str(m.get("token", "")),
                    provider="anonymmail",
                    from_email=m.get("from", "unknown"),
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("date", "")),
                    body_text=m.get("body", ""),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        # Same endpoint, filter by token
        emails = self.list_emails(address)
        for e in emails:
            if e.id == email_id:
                return e
        return None
