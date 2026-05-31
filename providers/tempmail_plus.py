"""TempMail.plus provider — REST API with domain discovery."""

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


class TempMailPlusClient(TempMailClient):
    """Client for https://tempmail.plus/"""

    BASE_URL = "https://tempmail.plus/api"

    @property
    def provider_name(self) -> str:
        return "tempmail.plus"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._epin = ""

    def _get_domains(self) -> list:
        """Scrape valid domains from the homepage."""
        if BeautifulSoup is None:
            return ["mailto.plus"]
        resp = self._session.get("https://tempmail.plus/en/", timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            menus = soup.find_all("div", {"class": "dropdown-menu"})
            if len(menus) >= 2:
                return [btn.text.strip() for btn in menus[1].find_all("button") if btn.text.strip()]
        return ["mailto.plus"]

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        selected = domain if domain and domain in domains else (domains[0] if domains else "mailto.plus")
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@{selected}"
        return TempEmail(address=address, provider="tempmail.plus")

    def list_emails(self, address: str) -> list:
        name, domain = address.split("@", 1)
        resp = self._session.get(
            f"{self.BASE_URL}/mails",
            params={"email": f"{name}@{domain}", "limit": 100, "epin": self._epin},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            result = []
            for m in data.get("mail_list", []):
                result.append(InboxEmail(
                    id=str(m.get("mail_id", "")),
                    provider="tempmail.plus",
                    from_email=m.get("from", "unknown"),
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("time", "")),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        resp = self._session.get(
            f"{self.BASE_URL}/mails/{email_id}",
            params={"email": address, "epin": self._epin},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            return InboxEmail(
                id=email_id,
                provider="tempmail.plus",
                from_email=data.get("from", "unknown"),
                subject=data.get("subject", "(no subject)"),
                received_at=str(data.get("time", "")),
                body_html=data.get("html", ""),
            )
        return None
