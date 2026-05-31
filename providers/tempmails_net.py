"""Tempmails.net provider — CSRF + REST API."""

import time
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


class TempmailsNetClient(TempMailClient):
    """Client for https://tempmails.net/"""

    BASE_URL = "https://tempmails.net"

    @property
    def provider_name(self) -> str:
        return "tempmails.net"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "x-requested-with": "XMLHttpRequest",
        })
        self._token = ""

    def _init_session(self):
        resp = self._session.get(self.BASE_URL, timeout=self._timeout)
        if resp.status_code == 200 and BeautifulSoup:
            soup = BeautifulSoup(resp.text, "html.parser")
            meta = soup.find("meta", {"name": "csrf-token"})
            if meta:
                self._token = meta.get("content", "")
                self._session.headers["x-csrf-token"] = self._token

    def _get_domains(self) -> list:
        if not BeautifulSoup:
            return ["tempmails.net"]
        resp = self._session.get(f"{self.BASE_URL}/change", timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            select = soup.find("select", {"name": "domain"})
            if select:
                return [opt.get("value", "") for opt in select.find_all("option") if opt.get("value")]
        return ["tempmails.net"]

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        if not self._token:
            self._init_session()
        # Get initial mailbox
        ts = int(time.time() * 1000)
        resp = self._session.get(f"{self.BASE_URL}/messages?_={ts}", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            email = data.get("mailbox", "")
            if email:
                return TempEmail(address=email, provider="tempmails.net")
        # Create new
        domains = self._get_domains()
        selected = domain if domain and domain in domains else (domains[0] if domains else "tempmails.net")
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@{selected}"
        self._session.post(f"{self.BASE_URL}/create", data={
            "_token": self._token, "name": name, "domain": selected,
        }, timeout=self._timeout)
        return TempEmail(address=address, provider="tempmails.net")

    def list_emails(self, address: str) -> list:
        if not BeautifulSoup:
            raise TempMailError("beautifulsoup4 required")
        ts = int(time.time() * 1000)
        resp = self._session.get(f"{self.BASE_URL}/messages?_={ts}", timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            messages = data.get("messages", "")
            if not messages or messages == "":
                return []
            soup = BeautifulSoup(messages, "html.parser")
            result = []
            for a in soup.find_all("a", {"class": "email"}):
                try:
                    lis = a.find_all("li")
                    eid = a.get("href", "").rsplit("/", 1)[-1]
                    result.append(InboxEmail(
                        id=eid,
                        provider="tempmails.net",
                        from_email=lis[0].text.strip() if lis else "unknown",
                        subject=lis[1].text.strip() if len(lis) > 1 else "(no subject)",
                    ))
                except Exception:
                    continue
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        if not BeautifulSoup:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.get(f"{self.BASE_URL}/view/{email_id}", timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            main = soup.find("div", {"class": "textHolder text-center"})
            if main:
                spans = main.find_all("span")
                time_str = spans[-1].text.strip() if spans else ""
                p = main.find("p", {"class": "head"})
                content = "".join(str(s) for s in p.find_next_siblings()) if p else resp.text[:5000]
                return InboxEmail(id=email_id, provider="tempmails.net", received_at=time_str, body_html=content)
        return None
