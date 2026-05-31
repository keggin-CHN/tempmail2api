"""Eztempmail.com provider — CSRF + REST API."""

from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class EztempmailClient(TempMailClient):
    """Client for https://www.eztempmail.com/"""

    BASE_URL = "https://www.eztempmail.com"

    @property
    def provider_name(self) -> str:
        return "eztempmail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
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
        resp = self._session.post(f"{self.BASE_URL}/get_messages", data={
            "_token": self._token,
        }, timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            email = data.get("mailbox", "")
            if email:
                return TempEmail(address=email, provider="eztempmail")
        raise TempMailError(f"Failed to create email: {resp.status_code}")

    def list_emails(self, address: str) -> list:
        resp = self._session.post(f"{self.BASE_URL}/get_messages", data={
            "_token": self._token,
        }, timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            messages = data.get("messages", "")
            if not messages or messages == "":
                return []
            if BeautifulSoup:
                soup = BeautifulSoup(messages, "html.parser")
                result = []
                for a in soup.find_all("a", {"class": "ws-generate-email-1"}):
                    try:
                        lis = a.find_all("li")
                        eid = a.get("href", "").rsplit("/", 1)[-1]
                        result.append(InboxEmail(
                            id=eid,
                            provider="eztempmail",
                            from_email=lis[0].text.strip() if lis else "unknown",
                            subject=lis[1].text.strip() if len(lis) > 1 else "(no subject)",
                            received_at=lis[2].text.strip() if len(lis) > 2 else "",
                        ))
                    except Exception:
                        continue
                return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        resp = self._session.get(f"{self.BASE_URL}/view/{email_id}", timeout=self._timeout)
        if resp.status_code == 200:
            if BeautifulSoup:
                soup = BeautifulSoup(resp.text, "html.parser")
                main = soup.find("p", {"class": "d-flex mb-0"})
                html = str(main.span) if main and main.span else resp.text[:5000]
            else:
                html = resp.text[:5000]
            return InboxEmail(id=email_id, provider="eztempmail", body_html=html)
        return None
