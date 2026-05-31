"""Moakt.com provider — HTML scraping with BeautifulSoup."""

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


class MoaktClient(TempMailClient):
    """Client for https://moakt.com/"""

    @property
    def provider_name(self) -> str:
        return "moakt"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._created = False
        self._name = ""
        self._domain = ""

    def _get_domains(self) -> list:
        if BeautifulSoup is None:
            return ["mocake.com"]
        resp = self._session.get("https://moakt.com/", timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            select = soup.find("select", {"id": "domains"})
            if select:
                return [opt["value"] for opt in select.find_all("option") if opt.get("value")]
        return ["mocake.com"]

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        selected = domain if domain and domain in domains else (domains[0] if domains else "mocake.com")
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        self._name = name
        self._domain = selected
        address = f"{name}@{selected}"
        # Create the email on moakt
        self._session.post("https://moakt.com/en/inbox", data={
            "domain": selected,
            "username": name,
            "setemail": "Create",
            "preferred_domain": "",
        }, timeout=self._timeout)
        self._created = True
        return TempEmail(address=address, provider="moakt")

    def list_emails(self, address: str) -> list:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.get("https://moakt.com/en/inbox", timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            email_list = soup.find("div", {"id": "email_message_list"})
            if not email_list:
                return []
            result = []
            for row in email_list.find_all("tr")[1:-3]:
                try:
                    td = row.td
                    if td and td.a:
                        href = td.a.get("href", "")
                        eid = href.rsplit("/", 1)[-1] if "/" in href else ""
                        sender_td = row.find("td", {"id": "email-sender"})
                        sender = sender_td.text.strip() if sender_td else "unknown"
                        result.append(InboxEmail(
                            id=eid,
                            provider="moakt",
                            from_email=sender,
                            subject=td.a.text.strip(),
                        ))
                except Exception:
                    continue
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        resp = self._session.get(
            f"https://moakt.com/en/email/{email_id}/content/",
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            return InboxEmail(
                id=email_id,
                provider="moakt",
                body_html=resp.text,
            )
        return None
