"""Mail.gw provider — same API structure as mail.tm, different base URL."""

import random
import string
from typing import Optional

try:
    from curl_cffi import requests as cffi_requests
except ImportError:
    import requests as cffi_requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class MailGwClient(TempMailClient):
    """Client for https://mail.gw/ (same API as mail.tm)."""

    BASE_URL = "https://api.mail.gw"

    @property
    def provider_name(self) -> str:
        return "mail.gw"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = cffi_requests.Session(impersonate="chrome136")
        self._token: Optional[str] = None
        self._password: str = "TmpMail2api!"

    def _get_domains(self) -> list:
        resp = self._session.get(f"{self.BASE_URL}/domains", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            domains = data.get("hydra:member", data.get("domains", []))
            return [d["domain"] for d in domains if d.get("isActive", True)]
        return []

    def _create_account(self, address: str) -> dict:
        resp = self._session.post(
            f"{self.BASE_URL}/accounts",
            json={"address": address, "password": self._password},
            timeout=self._timeout,
        )
        if resp.status_code in (200, 201):
            return resp.json()
        raise TempMailError(f"Create account failed: {resp.status_code} {resp.text[:200]}")

    def _get_token(self, address: str) -> str:
        resp = self._session.post(
            f"{self.BASE_URL}/token",
            json={"address": address, "password": self._password},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            return resp.json().get("token", "")
        raise TempMailError(f"Get token failed: {resp.status_code}")

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        if not domains:
            raise TempMailError("No domains available")
        selected = domain if domain and domain in domains else domains[0]
        import random, string
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@{selected}"
        self._create_account(address)
        self._token = self._get_token(address)
        return TempEmail(address=address, provider="mail.gw")

    def _auth_headers(self) -> dict:
        if self._token:
            return {"Authorization": f"Bearer {self._token}"}
        return {}

    def list_emails(self, address: str) -> list:
        headers = self._auth_headers()
        resp = self._session.get(
            f"{self.BASE_URL}/messages",
            headers=headers,
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            messages = data.get("hydra:member", data.get("messages", []))
            result = []
            for m in messages:
                result.append(InboxEmail(
                    id=str(m.get("id", "")),
                    provider="mail.gw",
                    from_email=m.get("from", {}).get("address", "unknown") if isinstance(m.get("from"), dict) else str(m.get("from", "unknown")),
                    subject=m.get("subject", "(no subject)"),
                    received_at=m.get("createdAt", ""),
                    body_text=m.get("text", ""),
                    body_html=m.get("html", ""),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        headers = self._auth_headers()
        resp = self._session.get(
            f"{self.BASE_URL}/messages/{email_id}",
            headers=headers,
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            m = resp.json()
            return InboxEmail(
                id=str(m.get("id", "")),
                provider="mail.gw",
                from_email=m.get("from", {}).get("address", "unknown") if isinstance(m.get("from"), dict) else str(m.get("from", "unknown")),
                subject=m.get("subject", "(no subject)"),
                received_at=m.get("createdAt", ""),
                body_text=m.get("text", ""),
                body_html=m.get("html", ""),
            )
        return None
