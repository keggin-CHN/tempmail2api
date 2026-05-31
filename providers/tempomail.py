"""Tempomail.top provider — REST API with free API key."""

import random
import string
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class TempomailClient(TempMailClient):
    """Client for https://tempomail.top/"""

    BASE_URL = "https://api.tempomail.top/api/v1"

    @property
    def provider_name(self) -> str:
        return "tempomail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._apikey: Optional[str] = None

    def _ensure_apikey(self):
        if self._apikey:
            return
        resp = self._session.get(f"{self.BASE_URL}/getApiKey", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            status = data.get("body", {}).get("data", {}).get("apiKey")
            if status:
                self._apikey = status
                self._session.headers.update({"Authorization": f"Bearer {self._apikey}"})
                return
        raise TempMailError("Failed to get API key")

    def _get_domains(self) -> list:
        self._ensure_apikey()
        resp = self._session.get(
            f"{self.BASE_URL}/domains",
            params={"apiKey": self._apikey, "limit": 50, "offset": 0, "domain": ""},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            domains = data.get("body", {}).get("data", {}).get("domains", [])
            return [d["name"] for d in domains]
        return []

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        self._ensure_apikey()
        domains = self._get_domains()
        if not domains:
            raise TempMailError("No domains available")
        selected = domain if domain and domain in domains else domains[0]
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        resp = self._session.post(
            f"{self.BASE_URL}/mail?apiKey={self._apikey}",
            json={"apiKey": self._apikey, "domain": selected, "mail": name},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            address = f"{name}@{selected}"
            return TempEmail(address=address, provider="tempomail")
        raise TempMailError(f"Failed to create email: {resp.status_code}")

    def list_emails(self, address: str) -> list:
        self._ensure_apikey()
        resp = self._session.get(
            f"{self.BASE_URL}/mail/messages",
            params={"mail": address, "offset": 0, "limit": 50},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            messages = data.get("body", {}).get("data", {}).get("messages", {})
            rows = messages.get("rows", [])
            result = []
            for m in rows:
                result.append(InboxEmail(
                    id=str(m.get("id", "")),
                    provider="tempomail",
                    from_email=m.get("from", "unknown"),
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("date", "")),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        self._ensure_apikey()
        resp = self._session.get(
            f"{self.BASE_URL}/mail/messages/message/{email_id}",
            params={"mail": address},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            messages = data.get("body", {}).get("data", {}).get("messages", [])
            if messages:
                m = messages[0].get("data", {})
                return InboxEmail(
                    id=email_id,
                    provider="tempomail",
                    from_email=m.get("from", "unknown"),
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("date", "")),
                    body_html=m.get("html", ""),
                    body_text=m.get("text", ""),
                )
        return None
