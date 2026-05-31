"""Muellmail.com provider — GraphQL API."""

import random
import string
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class MuellmailClient(TempMailClient):
    """Client for https://muellmail.com/"""

    BASE_URL = "https://muellmail.com"

    @property
    def provider_name(self) -> str:
        return "muellmail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        self._token = ""

    def _init_session(self):
        """Get session and CSRF token."""
        self._session.get(f"{self.BASE_URL}/api/f-auth/session", timeout=self._timeout)
        resp = self._session.get(f"{self.BASE_URL}/api/f-auth/csrf", timeout=self._timeout)
        if resp.status_code == 200:
            self._token = resp.json().get("csrfToken", "")

    def _get_domains(self) -> list:
        try:
            from bs4 import BeautifulSoup
        except ImportError:
            return ["muellmail.com"]
        resp = self._session.get(self.BASE_URL, timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            select = soup.find("div", {"id": "generateMail"})
            if select:
                return [opt["value"] for opt in select.find_all("option") if opt.get("value")]
        return ["muellmail.com"]

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        if not self._token:
            self._init_session()
        domains = self._get_domains()
        selected = domain if domain and domain in domains else (domains[0] if domains else "muellmail.com")
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@{selected}"
        self._session.post(f"{self.BASE_URL}/api/f-auth/callback/anon?", data={
            "redirect": "false",
            "muellmail": address,
            "csrfToken": self._token,
            "callbackUrl": f"{self.BASE_URL}/#/{address}",
            "json": "true",
        }, timeout=self._timeout)
        self._session.get(f"{self.BASE_URL}/api/auth/session", timeout=self._timeout)
        return TempEmail(address=address, provider="muellmail")

    def list_emails(self, address: str) -> list:
        resp = self._session.post(f"{self.BASE_URL}/graphql", json={
            "operationName": "MailQuery",
            "variables": {"offset": 0, "limit": 100},
            "query": "query MailQuery($offset: Int!, $limit: Int!) {\n  emails(orderBy: {createdAt: desc}, offset: $offset, limit: $limit) {\n    id\n    subject\n    sender\n    createdAt\n    html\n    text\n    }\n}",
        }, timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            emails = data.get("data", {}).get("emails", [])
            result = []
            for m in emails:
                result.append(InboxEmail(
                    id=str(m.get("id", "")),
                    provider="muellmail",
                    from_email=m.get("sender", "unknown"),
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("createdAt", "")),
                    body_html=m.get("html", ""),
                    body_text=m.get("text", ""),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        emails = self.list_emails(address)
        for e in emails:
            if e.id == email_id:
                return e
        return None
