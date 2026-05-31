"""Tempm.com provider — HTML scraping with BeautifulSoup (Generatoremail pattern)."""

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


class TempmClient(TempMailClient):
    """Client for https://tempm.com/"""

    BASE_URL = "https://tempm.com"

    @property
    def provider_name(self) -> str:
        return "tempm"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def _get_domains(self) -> list:
        if BeautifulSoup is None:
            return ["royal.net"]
        resp = self._session.get(self.BASE_URL, timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            return [d.text.strip() for d in soup.find_all("div", {"class": "tt-suggestion"}) if d.text.strip()]
        return ["royal.net"]

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        if not domains:
            raise TempMailError("No domains available")
        selected = domain if domain and domain in domains else domains[0]
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        return TempEmail(address=f"{name}@{selected}", provider="tempm")

    def list_emails(self, address: str) -> list:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        name, domain = address.split("@", 1)
        resp = self._session.get(f"{self.BASE_URL}/{domain}/{name}/", timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            email_table = soup.find("div", {"id": "email-table"})
            if not email_table:
                return []
            result = []
            for row in email_table.find_all("div", {"class": "row"}):
                try:
                    link = row.find("a")
                    if link and link.get("href"):
                        eid = link["href"].rsplit("/", 1)[-1]
                        result.append(InboxEmail(
                            id=eid, provider="tempm",
                            subject=link.get_text(strip=True),
                        ))
                except Exception:
                    continue
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        name, domain = address.split("@", 1)
        resp = self._session.get(f"{self.BASE_URL}/{domain}/{name}/{email_id}", timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            body = soup.find("div", {"class": "mess_bodiyy"})
            html = str(body) if body else resp.text[:5000]
            return InboxEmail(id=email_id, provider="tempm", body_html=html)
        return None
