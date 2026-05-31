"""Moakt.com — form POST + HTML parsing."""

from typing import List, Optional
import re

import requests
from bs4 import BeautifulSoup

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailFetchError


class MoaktClient(TempMailClient):
    """Client for https://moakt.com/."""

    BASE_URL = "https://moakt.com"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self._address: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "moakt"

    def _ensure_session(self):
        if self._address:
            return

        # First get session
        resp = self._session.get(self.BASE_URL, timeout=15)
        resp.raise_for_status()

        # POST to create random email
        resp2 = self._session.post(f"{self.BASE_URL}/en/inbox", data={
            'random': 'Get a Random Address'
        }, timeout=15, allow_redirects=True)
        resp2.raise_for_status()

        soup = BeautifulSoup(resp2.text, 'html.parser')

        # Find email address
        email_el = soup.find('span', {'id': 'email-address'})
        if email_el:
            self._address = email_el.text.strip()
        
        if not self._address:
            # Try regex
            emails = re.findall(r'[\w.-]+@[\w.-]+\.\w+', resp2.text[:10000])
            for e in emails:
                if '@' in e and 'example' not in e and len(e) < 50:
                    self._address = e
                    break

        if not self._address:
            raise TempMailError("无法创建邮箱")

    def generate_email(self) -> TempEmail:
        self._ensure_session()
        return TempEmail(address=self._address, provider="moakt")

    def list_emails(self, address: str) -> List[InboxEmail]:
        self._ensure_session()

        resp = self._session.get(f"{self.BASE_URL}/en/inbox", timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        result = []
        # Find message rows in table
        table = soup.find('table')
        if table:
            rows = table.find_all('tr')
            for row in rows:
                cells = row.find_all('td')
                if len(cells) >= 3:
                    subject = cells[0].get_text(strip=True)
                    sender = cells[1].get_text(strip=True)
                    link = cells[0].find('a')
                    email_id = link.get('href', '').split('/')[-1] if link else ''
                    if subject and subject != 'Message Title':
                        result.append(InboxEmail(
                            id=email_id,
                            from_address=sender,
                            subject=subject,
                            date='',
                            body_html='',
                            body_text='',
                            provider="moakt",
                            address=address or self._address or "",
                        ))

        return result

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        self._ensure_session()

        resp = self._session.get(f"{self.BASE_URL}/en/mail/{email_id}", timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Find email content
        content = soup.find('div', {'id': 'email-content'})
        if not content:
            content = soup.find(class_='email-body')
        
        body_html = str(content) if content else ''
        
        # Find sender and subject
        sender = ''
        subject = ''
        for th in soup.find_all(['th', 'td']):
            text = th.get_text(strip=True)
            if text.startswith('From:'):
                sender = text.replace('From:', '').strip()
            elif text.startswith('Subject:'):
                subject = text.replace('Subject:', '').strip()

        return InboxEmail(
            id=email_id,
            from_address=sender,
            subject=subject,
            date='',
            body_html=body_html,
            body_text='',
            provider="moakt",
            address=address or self._address or "",
        )
