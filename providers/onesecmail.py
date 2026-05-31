"""1SecMail.com provider — clean REST API."""

import random
import string
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class OnesecmailClient(TempMailClient):
    """Client for https://www.1secmail.com/"""

    BASE_URL = "https://www.1secmail.com/api/v1"

    @property
    def provider_name(self) -> str:
        return "1secmail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def _get_domains(self) -> list:
        resp = self._session.get(f"{self.BASE_URL}/", params={"action": "getDomainList"}, timeout=self._timeout)
        if resp.status_code == 200:
            return resp.json()
        return []

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        if not domains:
            raise TempMailError("No domains available")
        selected = domain if domain and domain in domains else domains[0]
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        return TempEmail(address=f"{name}@{selected}", provider="1secmail")

    def list_emails(self, address: str) -> list:
        name, domain = address.split("@", 1)
        resp = self._session.get(
            f"{self.BASE_URL}/",
            params={"action": "getMessages", "login": name, "domain": domain},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            result = []
            for m in resp.json():
                result.append(InboxEmail(
                    id=str(m.get("id", "")),
                    provider="1secmail",
                    from_email=m.get("from", "unknown"),
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("date", "")),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        name, domain = address.split("@", 1)
        resp = self._session.get(
            f"{self.BASE_URL}/",
            params={"action": "readMessage", "login": name, "domain": domain, "id": email_id},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            return InboxEmail(
                id=email_id,
                provider="1secmail",
                from_email=data.get("from", "unknown"),
                subject=data.get("subject", "(no subject)"),
                received_at=str(data.get("date", "")),
                body_html=data.get("body", data.get("html", "")),
                body_text=data.get("textBody", ""),
            )
        return None
