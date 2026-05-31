"""Lroid.com provider — Tempail pattern (same as Haribu)."""

import random
import string
import re
from typing import List, Optional
from curl_cffi import requests as curl_requests
from bs4 import BeautifulSoup

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailFetchError


class LroidClient(TempMailClient):
    """Client for https://lroid.com — Tempail pattern."""

    BASE_URL = "https://lroid.com"

    def __init__(self):
        self._session = curl_requests.Session(impersonate="chrome136")
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': self.BASE_URL,
        })
        self._address: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "lroid"

    def generate_email(self) -> TempEmail:
        resp = self._session.get(self.BASE_URL, timeout=15)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        # Get generated email
        inp = soup.find('input', {'id': 'eposta_adres'})
        if inp and inp.get('value', '').strip():
            self._address = inp['value'].strip()
        else:
            # Fallback: random
            name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
            self._address = f"{name}@yevme.com"

        return TempEmail(address=self._address, provider="lroid")

    def list_emails(self, address: str) -> List[InboxEmail]:
        resp = self._session.get(f"{self.BASE_URL}/en/api-kontrol/", timeout=15)
        resp.raise_for_status()

        result = []
        soup = BeautifulSoup(resp.text, 'html.parser')
        rows = soup.find_all('tr')

        for idx, row in enumerate(rows):
            cols = row.find_all('td')
            if len(cols) >= 3:
                sender = cols[0].get_text(strip=True)
                subject = cols[1].get_text(strip=True)
                date_str = cols[2].get_text(strip=True)

                # Skip header rows
                if sender in ('Sender', 'Gönderen', '') and subject in ('Subject', 'Konu', ''):
                    continue

                if sender or subject:
                    result.append(InboxEmail(
                        id=str(idx),
                        from_address=sender,
                        subject=subject,
                        date=date_str,
                        body_html="",
                        body_text="",
                        provider="lroid",
                        address=address or self._address or "",
                    ))

        return result

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        # Use api-oku to read email
        resp = self._session.get(f"{self.BASE_URL}/en/api-oku/{email_id}", timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')
        body_html = str(soup)
        body_text = soup.get_text(separator='\n', strip=True)

        return InboxEmail(
            id=email_id,
            from_address="",
            subject="",
            date="",
            body_html=body_html,
            body_text=body_text,
            provider="lroid",
            address=address or self._address or "",
        )
