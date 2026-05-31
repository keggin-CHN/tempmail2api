"""Fakermail.com provider — REST API."""

import random
import string
from hashlib import sha1
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class FakermailClient(TempMailClient):
    """Client for https://fakermail.com/"""

    BASE_URL = "https://fakermail.com"

    @property
    def provider_name(self) -> str:
        return "fakermail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def _get_domains(self) -> list:
        resp = self._session.get(f"{self.BASE_URL}/api/domains", timeout=self._timeout)
        if resp.status_code == 200:
            return resp.json()
        return []

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        if not domains:
            raise TempMailError("No domains available")
        selected = domain if domain and domain in domains else domains[0]
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        return TempEmail(address=f"{name}@{selected}", provider="fakermail")

    def list_emails(self, address: str) -> list:
        email_hash = sha1(address.encode()).hexdigest()
        resp = self._session.get(f"{self.BASE_URL}/api/mail/{email_hash}", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                result = []
                for m in data:
                    result.append(InboxEmail(
                        id=str(m.get("id", hash(str(m)))),
                        provider="fakermail",
                        from_email=m.get("from", "unknown"),
                        subject=m.get("subject", "(no subject)"),
                        received_at=str(m.get("date", "")),
                    ))
                return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        emails = self.list_emails(address)
        for e in emails:
            if e.id == email_id:
                return e
        return None
