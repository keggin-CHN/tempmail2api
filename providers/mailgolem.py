"""Mailgolem.com provider — CSRF + REST API."""

import random
import string
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class MailgolemClient(TempMailClient):
    """Client for https://mailgolem.com/"""

    BASE_URL = "https://mailgolem.com"

    @property
    def provider_name(self) -> str:
        return "mailgolem"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._token = ""
        self._init()

    def _init(self):
        resp = self._session.get(self.BASE_URL, timeout=self._timeout)
        if resp.status_code == 200 and BeautifulSoup:
            soup = BeautifulSoup(resp.text, "html.parser")
            meta = soup.find("meta", {"name": "csrf-token"})
            if meta:
                self._token = meta.get("content", "")

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@mailgolem.com"
        return TempEmail(address=address, provider="mailgolem")

    def list_emails(self, address: str) -> list:
        resp = self._session.post(
            f"{self.BASE_URL}/fetch-emails/{address}",
            data={"_token": self._token},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            result = []
            for m in resp.json():
                result.append(InboxEmail(
                    id=str(m.get("id", "")),
                    provider="mailgolem",
                    from_email=m.get("from", "unknown"),
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("created_at", "")),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.get(f"{self.BASE_URL}/view/{email_id}", timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            body_script = soup.find("script", {"data-cfasync": "false"})
            if body_script and body_script.next_sibling:
                try:
                    from base64 import b64decode
                    from urllib.parse import unquote as urldecode
                    b64_data = body_script.next_sibling.text.split('decodeURIComponent(atob("', 1)[1].split('"', 1)[0]
                    html = urldecode(b64decode(b64_data).decode())
                    return InboxEmail(id=email_id, provider="mailgolem", body_html=html)
                except Exception:
                    pass
            return InboxEmail(id=email_id, provider="mailgolem", body_html=resp.text[:5000])
        return None
