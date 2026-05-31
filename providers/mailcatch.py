"""MailCatch.com provider — simple REST API."""

import random
import string
import re
from typing import List, Optional
from curl_cffi import requests as curl_requests

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailFetchError


class MailcatchClient(TempMailClient):
    """Client for https://mailcatch.com — simple REST API."""

    BASE_URL = "https://mailcatch.com"

    def __init__(self):
        self._session = curl_requests.Session(impersonate="chrome136")
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': self.BASE_URL,
        })
        self._address: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "mailcatch"

    def generate_email(self) -> TempEmail:
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        self._address = f"{name}@mailcatch.com"
        return TempEmail(address=self._address, provider="mailcatch")

    def list_emails(self, address: str) -> List[InboxEmail]:
        if BeautifulSoup is None:
            raise TempMailError("需要安装 beautifulsoup4")

        inbox_name = address.split("@")[0] if "@" in address else address
        url = f"{self.BASE_URL}/api/list/{inbox_name}"

        resp = self._session.get(url, timeout=15)
        resp.raise_for_status()

        result = []
        soup = BeautifulSoup(resp.text, 'html.parser')

        for item in soup.find_all(class_='email-item'):
            email_id = item.get('data-email-id', '')
            subject = item.get('data-subject', '')
            sender = item.get('data-sender', '')
            timestamp = item.get('data-timestamp', '')

            if email_id:
                result.append(InboxEmail(
                    id=str(email_id),
                    from_address=sender,
                    subject=subject,
                    date=timestamp,
                    body_html="",
                    body_text="",
                    provider="mailcatch",
                    address=address,
                ))

        return result

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        inbox_name = address.split("@")[0] if "@" in address else address
        url = f"{self.BASE_URL}/api/data/{inbox_name}/{email_id}"

        resp = self._session.get(url, timeout=15)
        resp.raise_for_status()

        body_html = resp.text
        body_text = ""
        if BeautifulSoup:
            soup = BeautifulSoup(body_html, 'html.parser')
            body_text = soup.get_text(separator='\n', strip=True)

        return InboxEmail(
            id=email_id,
            from_address="",
            subject="",
            date="",
            body_html=body_html,
            body_text=body_text,
            provider="mailcatch",
            address=address,
        )
