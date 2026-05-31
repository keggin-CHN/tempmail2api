"""Mailsac.com provider — HTML scraping with BeautifulSoup."""

import json
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


class MailsacClient(TempMailClient):
    """Client for https://mailsac.com/"""

    @property
    def provider_name(self) -> str:
        return "mailsac"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@mailsac.com"
        return TempEmail(address=address, provider="mailsac")

    def list_emails(self, address: str) -> list:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        name, domain = address.split("@", 1)
        resp = self._session.get(
            f"https://mailsac.com/inbox/{name}%40{domain}",
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            containers = soup.find_all("div", {"class": "container-fluid"}, limit=2)
            if len(containers) < 2:
                return []
            script = containers[1].find("script")
            if not script or not script.text:
                return []
            try:
                marker = "window.__seedInboxMessages = "
                data_str = script.text.split(marker, 1)[1].rsplit(";\nwindow.__inboxUntil", 1)[0]
                data = json.loads(data_str)
                result = []
                for m in data:
                    froms = m.get("from", [])
                    from_email = froms[0].get("address", "unknown") if froms else "unknown"
                    result.append(InboxEmail(
                        id=str(m.get("_id", "")),
                        provider="mailsac",
                        from_email=from_email,
                        subject=m.get("subject", "(no subject)"),
                        received_at=str(m.get("received", "")),
                    ))
                # First email also has body
                if result and data:
                    result[0].body_html = data[0].get("body", "")
                return result
            except (IndexError, json.JSONDecodeError, KeyError):
                return []
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        emails = self.list_emails(address)
        for e in emails:
            if e.id == email_id:
                return e
        return None
