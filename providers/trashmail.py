"""Trashmail.com provider — HTML scraping with BeautifulSoup."""

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


class TrashmailClient(TempMailClient):
    """Client for https://www.trash-mail.com/"""

    BASE_URL = "https://www.trash-mail.com"

    @property
    def provider_name(self) -> str:
        return "trashmail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._password = "123"

    def _get_domains(self) -> tuple:
        """Returns (domains, flags) where flags indicate password requirement."""
        if BeautifulSoup is None:
            return ["trash-mail.com"]
        resp = self._session.get(f"{self.BASE_URL}/inbox/", verify=False, timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            select = soup.find("select", {"id": "form-domain-id"})
            if select:
                domains = []
                for opt in select.find_all("option"):
                    val = opt.get("value", "")
                    if val:
                        domain = val.split("---")[0] if "---" in val else val
                        domains.append(domain)
                return domains
        return ["trash-mail.com"]

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        if not domains:
            raise TempMailError("No domains available")
        selected = domain if domain and domain in domains else domains[0]
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@{selected}"
        # Create the email
        self._session.post(f"{self.BASE_URL}/inbox/", data={
            "form-postbox": name,
            "form-domain": f"{selected}---1",
            "form-password": self._password,
        }, verify=False, timeout=self._timeout)
        return TempEmail(address=address, provider="trashmail")

    def list_emails(self, address: str) -> list:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.get(f"{self.BASE_URL}/inbox/", verify=False, timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            table = soup.find("table", {"class": "table-striped"})
            if not table:
                return []
            result = []
            for td in table.find_all("td", {"class": "message-td"}):
                try:
                    a = td.find("a")
                    if not a:
                        continue
                    nr = a.get("nr", "")
                    sender = a.find("p", {"class": "message-from"})
                    subject = a.find("p", {"class": "message-subject"})
                    date = a.find("p", {"class": "message-date"})
                    result.append(InboxEmail(
                        id=str(nr),
                        provider="trashmail",
                        from_email=sender.text.strip() if sender else "unknown",
                        subject=subject.text.strip() if subject else "(no subject)",
                        received_at=date.text.strip() if date else "",
                    ))
                except Exception:
                    continue
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.get(
            f"{self.BASE_URL}/en/mail/message/id/{email_id}",
            verify=False, timeout=self._timeout,
        )
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            content = soup.find("div", {"class": "message-content"})
            html = str(content) if content else resp.text[:5000]
            return InboxEmail(id=email_id, provider="trashmail", body_html=html)
        return None
