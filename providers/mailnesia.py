"""Mailnesia.com provider — HTML scraping with BeautifulSoup."""

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


class MailnesiaClient(TempMailClient):
    """Client for https://mailnesia.com/"""

    @property
    def provider_name(self) -> str:
        return "mailnesia"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@mailnesia.com"
        return TempEmail(address=address, provider="mailnesia")

    def list_emails(self, address: str) -> list:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required: pip install beautifulsoup4 lxml")
        name = address.split("@")[0]
        resp = self._session.get(
            f"https://mailnesia.com/mailbox/{name}?noheadernofooter=1",
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            emails = soup.find_all("tr", {"class": "emailheader"})
            result = []
            for email in emails:
                try:
                    tds = email.find_all("td")
                    result.append(InboxEmail(
                        id=email.get("id", ""),
                        provider="mailnesia",
                        from_email=tds[1].text.strip() if len(tds) > 1 else "unknown",
                        subject=tds[3].text.strip() if len(tds) > 3 else "(no subject)",
                        received_at=tds[0].time.get("datetime", "") if tds[0].time else "",
                    ))
                except Exception:
                    continue
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        name = address.split("@")[0]
        resp = self._session.get(
            f"https://mailnesia.com/mailbox/{name}/{email_id}?noheadernofooter=1",
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            content_div = soup.find("div", {"id": f"text_html_{email_id}"})
            html = str(content_div) if content_div else resp.text
            return InboxEmail(
                id=email_id,
                provider="mailnesia",
                body_html=html,
            )
        return None
