"""Mail4QA.com — API key from app.js + REST API."""

import re
from typing import List, Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailFetchError


class Mail4qaClient(TempMailClient):
    """Client for https://mail4qa.com/ (REST API with API key)."""

    BASE_URL = "https://api.mail4qa.com"
    JS_URL = "https://console.mail4qa.com/assets/js/app.js"

    def __init__(self):
        try:
            from curl_cffi import requests as curl_requests
            self._session = curl_requests.Session(impersonate="chrome136")
        except ImportError:
            self._session = requests.Session()
        self._address: Optional[str] = None
        self._apikey: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "mail4qa.com"

    def _ensure_api(self):
        if self._apikey:
            return

        resp = self._session.get(self.JS_URL, timeout=15)
        resp.raise_for_status()

        match = re.search(r'x-apikey", "([^"]+)"', resp.text)
        if not match:
            raise TempMailError("无法获取 API key")

        self._apikey = match.group(1)
        self._session.headers.update({"X-Apikey": self._apikey})

    def generate_email(self) -> TempEmail:
        self._ensure_api()

        import random, string
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        self._address = f"{name}@mail4qa.com"
        return TempEmail(address=self._address, provider="mail4qa.com")

    def list_emails(self, address: str) -> List[InboxEmail]:
        self._ensure_api()
        addr = address or self._address
        if not addr:
            raise TempMailError("需要邮箱地址")

        name, domain = addr.split("@", 1)
        resp = self._session.get(
            f"{self.BASE_URL}/emails/inbox?email={name}%40{domain}&pagesize=50&cursor=0",
            timeout=15,
        )

        if resp.status_code == 404:
            return []
        resp.raise_for_status()

        data = resp.json()
        result = []

        if data.get("status") == "success":
            for email in data.get("emails", []):
                source = email.get("mail_source", {})
                from_data = source.get("from", {}).get("value", [{}])
                sender = from_data[0].get("address", "") if from_data else ""

                result.append(InboxEmail(
                    id=email.get("_id", ""),
                    from_address=sender,
                    subject=source.get("subject", ""),
                    date=source.get("date", ""),
                    body_html=source.get("html", ""),
                    body_text=source.get("text", ""),
                    provider="mail4qa.com",
                    address=addr,
                ))

        return result

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        self._ensure_api()

        resp = self._session.get(
            f"{self.BASE_URL}/emails/inbox?mid={email_id}",
            timeout=15,
        )
        resp.raise_for_status()

        data = resp.json()
        source = data.get("mail_source", {})
        from_data = source.get("from", {}).get("value", [{}])
        sender = from_data[0].get("address", "") if from_data else ""

        return InboxEmail(
            id=email_id,
            from_address=sender,
            subject=source.get("subject", ""),
            date=source.get("date", ""),
            body_html=source.get("html", ""),
            body_text=source.get("text", ""),
            provider="mail4qa.com",
            address=address or self._address or "",
        )
