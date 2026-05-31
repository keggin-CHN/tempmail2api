"""EmailOnDeck.com provider — AJAX API."""

import re
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class EmailondeckClient(TempMailClient):
    """Client for https://www.emailondeck.com/"""

    BASE_URL = "https://www.emailondeck.com"

    @property
    def provider_name(self) -> str:
        return "emailondeck"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._token = ""

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        resp = self._session.get(f"{self.BASE_URL}/ajax/ce-new-email.php", timeout=self._timeout)
        if resp.status_code != 200:
            raise TempMailError(f"Failed to create email: {resp.status_code}")
        parts = resp.text.split("|", 1)
        if len(parts) < 2:
            raise TempMailError(f"Unexpected response: {resp.text[:100]}")
        address, self._token = parts[0], parts[1]
        return TempEmail(address=address.strip(), provider="emailondeck")

    def list_emails(self, address: str) -> list:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.post(f"{self.BASE_URL}/ajax/messages.php", timeout=self._timeout)
        if resp.status_code == 200 and len(resp.text) > 1 and resp.text[0] != "0":
            soup = BeautifulSoup(resp.text.split("|", 3)[-1], "html.parser")
            result = []
            for email in soup.find_all("div", {"class": "inbox_rows msglink"}):
                try:
                    result.append(InboxEmail(
                        id=email.get("name", ""),
                        provider="emailondeck",
                        from_email=email.find("td", {"class": "desktop_only inbox_td_from"}).text.strip(),
                        subject=email.find("td", {"class": "desktop_only inbox_td_subject"}).text.strip(),
                        received_at=email.find("td", {"class": "inbox_td_received"}).text.strip(),
                    ))
                except Exception:
                    continue
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.get(
            f"{self.BASE_URL}/email_iframe.php?msg_id={email_id}",
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            content = soup.find("div", {"id": "inbox_message"})
            html = str(content) if content else resp.text
            return InboxEmail(
                id=email_id,
                provider="emailondeck",
                body_html=html,
            )
        return None
