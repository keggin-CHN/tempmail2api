"""Fakemail.net provider — Minuteinbox-style REST API."""

import random
import string
import json
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class FakemailNetClient(TempMailClient):
    """Client for https://www.fakemail.net/"""

    BASE_URL = "https://www.fakemail.net"

    @property
    def provider_name(self) -> str:
        return "fakemail.net"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        self._email = None

    def _init_email(self):
        """Create a new email by calling /index/index."""
        # First get CSRF token if needed
        resp = self._session.get(self.BASE_URL, timeout=self._timeout)
        if resp.status_code != 200:
            raise TempMailError(f"Failed to get session: {resp.status_code}")
        
        csrf = ""
        if 'const CSRF="' in resp.text:
            csrf = resp.text.split('const CSRF="', 1)[1].split('"', 1)[0]
        
        url = f"{self.BASE_URL}/index/index"
        if csrf:
            url += f"?csrf_token={csrf}"
        
        resp2 = self._session.get(url, timeout=self._timeout)
        if resp2.status_code == 200:
            data = json.loads(resp2.content.decode("utf-8-sig"))
            self._email = data.get("email", "")
            return self._email
        raise TempMailError(f"Failed to create email: {resp2.status_code}")

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        email_addr = self._init_email()
        if not email_addr:
            raise TempMailError("Failed to generate email")
        return TempEmail(address=email_addr, provider="fakemail.net")

    def list_emails(self, address: str) -> list:
        resp = self._session.get(f"{self.BASE_URL}/index/refresh", timeout=self._timeout)
        if resp.status_code == 200:
            # Response is HTML with table rows
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.find_all("tr")
            result = []
            for row in rows:
                tds = row.find_all("td")
                if len(tds) >= 4:
                    link = tds[0].find("a")
                    eid = ""
                    if link and link.get("href"):
                        eid = link["href"].rsplit("/", 1)[-1]
                    result.append(InboxEmail(
                        id=eid,
                        provider="fakemail.net",
                        from_email=tds[1].get_text(strip=True),
                        subject=tds[2].get_text(strip=True),
                        received_at=tds[3].get_text(strip=True) if len(tds) > 3 else "",
                    ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        resp = self._session.get(f"{self.BASE_URL}/email/id/{email_id}", timeout=self._timeout)
        if resp.status_code == 200:
            parts = resp.text.split("\n", 1)
            html = parts[1] if len(parts) > 1 else resp.text
            return InboxEmail(
                id=email_id,
                provider="fakemail.net",
                body_html=html,
            )
        return None
