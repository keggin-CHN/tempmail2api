"""Noopmail.org provider — simple REST API."""

import random
import string
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class NoopmailClient(TempMailClient):
    """Client for https://noopmail.org/"""

    BASE_URL = "https://noopmail.org/api"

    @property
    def provider_name(self) -> str:
        return "noopmail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json, text/plain, */*",
        })

    def _get_domains(self) -> list:
        resp = self._session.get(f"{self.BASE_URL}/d", timeout=self._timeout)
        if resp.status_code == 200:
            return resp.json()
        return []

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        if not domains:
            raise TempMailError("No domains available")
        selected = domain if domain and domain in domains else domains[0]
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@{selected}"
        return TempEmail(address=address, provider="noopmail")

    def list_emails(self, address: str) -> list:
        name, domain = address.split("@", 1)
        resp = self._session.post(
            f"{self.BASE_URL}/c",
            json={"e": name, "d": domain},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            result = []
            for m in data:
                result.append(InboxEmail(
                    id=str(m.get("id", "")),
                    provider="noopmail",
                    from_email=m.get("from", "unknown"),
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("date", "")),
                    body_text=m.get("text", ""),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        resp = self._session.get(f"{self.BASE_URL}/i/{email_id}", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            return InboxEmail(
                id=email_id,
                provider="noopmail",
                from_email=data.get("from", "unknown"),
                subject=data.get("subject", "(no subject)"),
                received_at=str(data.get("date", "")),
                body_html=data.get("html", ""),
                body_text=data.get("text", ""),
            )
        return None
