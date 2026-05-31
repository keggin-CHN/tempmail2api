"""Inboxes.com provider — REST API (successor of getnada.com)."""

import random
import string
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class InboxesClient(TempMailClient):
    """Client for https://inboxes.com/"""

    BASE_URL = "https://inboxes.com/api/v2"

    @property
    def provider_name(self) -> str:
        return "inboxes.com"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def _get_domains(self) -> list:
        resp = self._session.get(f"{self.BASE_URL}/domain", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            return [d["qdn"] for d in data.get("domains", [])]
        return []

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        if not domains:
            raise TempMailError("No domains available")
        selected = domain if domain and domain in domains else domains[0]
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@{selected}"
        return TempEmail(address=address, provider="inboxes.com")

    def list_emails(self, address: str) -> list:
        resp = self._session.get(f"{self.BASE_URL}/inbox/{address}", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            result = []
            for m in data.get("msgs", []):
                result.append(InboxEmail(
                    id=str(m.get("uid", "")),
                    provider="inboxes.com",
                    from_email=m.get("f", "unknown"),
                    subject=m.get("s", "(no subject)"),
                    received_at=str(m.get("cr", "")),
                    body_text=m.get("ph", ""),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        resp = self._session.get(f"{self.BASE_URL}/message/{email_id}", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            return InboxEmail(
                id=email_id,
                provider="inboxes.com",
                from_email=data.get("f", "unknown"),
                subject=data.get("s", "(no subject)"),
                received_at=str(data.get("cr", "")),
                body_html=data.get("html", ""),
            )
        return None
