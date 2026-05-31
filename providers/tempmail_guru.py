"""Tempmail.guru provider — Fake_trash_mail pattern."""

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


class TempmailGuruClient(TempMailClient):
    """Client for https://tempmail.guru/"""

    BASE_URL = "https://tempmail.guru"

    @property
    def provider_name(self) -> str:
        return "tempmail.guru"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        self._token = ""

    def _init_session(self):
        resp = self._session.get(self.BASE_URL, timeout=self._timeout)
        if resp.status_code == 200 and BeautifulSoup:
            soup = BeautifulSoup(resp.text, "html.parser")
            meta = soup.find("meta", {"name": "csrf-token"})
            if meta:
                self._token = meta.get("content", "")

    def _get_domains(self) -> list:
        if not BeautifulSoup:
            return ["tempmail.guru"]
        resp = self._session.get(f"{self.BASE_URL}/change", timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            select = soup.find("select", {"name": "domain"})
            if select:
                return [opt.text.strip() for opt in select.find_all("option") if opt.text.strip()]
        return ["tempmail.guru"]

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        if not self._token:
            self._init_session()
        domains = self._get_domains()
        selected = domain if domain and domain in domains else (domains[0] if domains else "tempmail.guru")
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@{selected}"
        # Create email via POST /messages
        self._session.post(f"{self.BASE_URL}/messages", data={
            "_token": self._token,
        }, timeout=self._timeout)
        return TempEmail(address=address, provider="tempmail.guru")

    def list_emails(self, address: str) -> list:
        if not BeautifulSoup:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.get(f"{self.BASE_URL}/inbox/{address}", timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            email_list = soup.find("ul", {"id": "email-list"})
            if not email_list:
                return []
            result = []
            for a in email_list.find_all("a"):
                try:
                    divs = a.find("div").find_all("div", recursive=False)
                    href = a.get("href", "")
                    eid = href.split("message-", 1)[-1].replace("/", "") if "message-" in href else ""
                    result.append(InboxEmail(
                        id=eid,
                        provider="tempmail.guru",
                        from_email=divs[0].p.text.strip() if divs[0].p else "unknown",
                        subject=divs[1].p.text.strip() if len(divs) > 1 and divs[1].p else "(no subject)",
                        received_at=divs[2].p.text.strip() if len(divs) > 2 and divs[2].p else "",
                    ))
                except Exception:
                    continue
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        name, domain = address.split("@", 1)
        resp = self._session.get(
            f"{self.BASE_URL}/email/{domain}/{name}/message-{email_id}/",
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            return InboxEmail(id=email_id, provider="tempmail.guru", body_html=resp.text)
        return None
