"""Fakemailgenerator.com provider — HTML scraping with BeautifulSoup."""

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


class FakemailgeneratorClient(TempMailClient):
    """Client for https://www.fakemailgenerator.com/"""

    BASE_URL = "https://www.fakemailgenerator.com"

    @property
    def provider_name(self) -> str:
        return "fakemailgenerator"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def _get_domains(self) -> list:
        if BeautifulSoup is None:
            return ["yuoia.com"]
        resp = self._session.get(self.BASE_URL, timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            dropdown = soup.find("ul", {"class": "dropdown-menu"})
            if dropdown:
                return [a.text.strip().lstrip("@") for a in dropdown.find_all("a") if a.text.strip()]
        return ["yuoia.com"]

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        if not domains:
            raise TempMailError("No domains available")
        selected = domain if domain and domain in domains else domains[0]
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        return TempEmail(address=f"{name}@{selected}", provider="fakemailgenerator")

    def list_emails(self, address: str) -> list:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        name, domain = address.split("@", 1)
        resp = self._session.get(f"{self.BASE_URL}/inbox/{domain}/{name}/", timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            email_list = soup.find("ul", {"id": "email-list"})
            if not email_list:
                return []
            result = []
            for email in email_list.find_all("a"):
                try:
                    divs = email.find("div").find_all("div", recursive=False)
                    href = email.get("href", "")
                    eid = href.split("message-", 1)[-1].replace("/", "") if "message-" in href else ""
                    result.append(InboxEmail(
                        id=eid,
                        provider="fakemailgenerator",
                        from_email=divs[0].p.text.strip() if divs[0].p else "unknown",
                        subject=divs[1].p.text.strip() if len(divs) > 1 and divs[1].p else "(no subject)",
                        received_at=divs[2].p.text.strip() if len(divs) > 2 and divs[2].p else "",
                    ))
                except Exception:
                    continue
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        name, domain = address.split("@", 1)
        resp = self._session.get(
            f"{self.BASE_URL}/email/{domain}/{self.name if hasattr(self, '_name') else name}/message-{email_id}/",
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            return InboxEmail(id=email_id, provider="fakemailgenerator", body_html=resp.text)
        return None
