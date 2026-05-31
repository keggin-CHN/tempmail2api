"""Tempail.com — Tempail pattern (HTML scraping)."""

from typing import List, Optional
import re

import requests
from bs4 import BeautifulSoup

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailFetchError


def _de_cf_email(encoded: str) -> str:
    """Decode Cloudflare email protection encoded string."""
    try:
        r = int(encoded[:2], 16)
        return ''.join(
            chr(int(encoded[i:i+2], 16) ^ r)
            for i in range(2, len(encoded), 2)
        )
    except Exception:
        return "unknown"


class TempailClient(TempMailClient):
    """Client for https://tempail.com/ (Tempail pattern)."""

    BASE_URL = "https://tempail.com"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self._address: Optional[str] = None
        self._oturum: Optional[str] = None
        self._tarih: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "tempail.com"

    def _ensure_session(self):
        if self._address:
            return

        resp = self._session.get(self.BASE_URL, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        # Find email address
        email_input = soup.find('input', {'id': 'eposta_adres'})
        if email_input:
            self._address = email_input.get('value', '')

        if not self._address:
            raise TempMailError("无法获取邮箱地址")

        # Find session values
        script_text = ''
        for sc in soup.find_all('script', src=False):
            text = sc.string or ''
            if 'oturum' in text:
                script_text = text
                break

        if script_text:
            oturum = re.search(r'var oturum="([^"]+)"', script_text)
            tarih = re.search(r'var tarih="([^"]+)"', script_text)
            self._oturum = oturum.group(1) if oturum else ''
            self._tarih = tarih.group(1) if tarih else ''

    def generate_email(self) -> TempEmail:
        self._ensure_session()
        return TempEmail(address=self._address, provider="tempail.com")

    def list_emails(self, address: str) -> List[InboxEmail]:
        self._ensure_session()

        resp = self._session.get(self.BASE_URL, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')
        result = []

        for mail in soup.find_all('li', {'class': 'mail'}):
            sender_div = mail.find('div', {'class': 'gonderen'})
            subject_div = mail.find('div', {'class': 'baslik'})
            time_div = mail.find('div', {'class': 'zaman'})

            sender = ''
            if sender_div:
                span = sender_div.find('span', {'data-cfemail': True})
                if span:
                    sender = _de_cf_email(span.get('data-cfemail', ''))
                else:
                    sender = sender_div.get_text(strip=True)

            subject = subject_div.get_text(strip=True) if subject_div else ''
            email_time = time_div.get_text(strip=True) if time_div else ''
            email_id = mail.get('id', '')

            result.append(InboxEmail(
                id=email_id,
                from_address=sender,
                subject=subject,
                date=email_time,
                body_html='',
                body_text='',
                provider="tempail.com",
                address=address or self._address or "",
            ))

        return result

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        self._ensure_session()

        resp = self._session.get(
            f"{self.BASE_URL}/mail/{email_id}", timeout=15
        )
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')

        content = soup.find('div', {'id': 'mail_content'})
        if not content:
            content = soup.find('div', {'class': 'e-mail-content'})

        body_html = str(content) if content else resp.text

        sender = ''
        subject = ''
        mail_info = soup.find('div', {'id': 'mail_info'})
        if mail_info:
            text = mail_info.get_text()
            from_match = re.search(r'From:\s*(.+)', text)
            subject_match = re.search(r'Subject:\s*(.+)', text)
            if from_match:
                sender = from_match.group(1).strip()
            if subject_match:
                subject = subject_match.group(1).strip()

        return InboxEmail(
            id=email_id,
            from_address=sender,
            subject=subject,
            date='',
            body_html=body_html,
            body_text='',
            provider="tempail.com",
            address=address or self._address or "",
        )
