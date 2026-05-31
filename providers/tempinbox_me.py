"""Temp-Inbox.me — form POST + HTML scraping (Livewire/CSRF)."""

import random
import string
from typing import List, Optional
import re

import requests
from bs4 import BeautifulSoup

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailFetchError


class TempInboxMeClient(TempMailClient):
    """Client for https://temp-inbox.me/."""

    BASE_URL = "https://temp-inbox.me"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self._address: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "temp-inbox.me"

    def _ensure_session(self):
        if self._address:
            return

        resp = self._session.get(self.BASE_URL, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf = soup.find('meta', {'name': 'csrf-token'})
        token = csrf.get('content', '') if csrf else ''

        # Get domains
        select = soup.find('select', {'id': 'selected_domain'})
        domains = []
        if select:
            domains = [opt.get('value', '') for opt in select.find_all('option') if opt.get('value')]

        domain = domains[0] if domains else 'temp-inbox.me'
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))

        # POST to create inbox
        self._session.headers.update({
            'X-CSRF-TOKEN': token,
            'X-Requested-With': 'XMLHttpRequest',
        })

        resp2 = self._session.post(f"{self.BASE_URL}/create/inbox", data={
            '_token': token,
            'userName': name,
            'selected_domain': domain,
            'email': f"{name}@{domain}",
        }, timeout=15, allow_redirects=True)
        resp2.raise_for_status()

        self._address = f"{name}@{domain}"

    def generate_email(self) -> TempEmail:
        self._ensure_session()
        return TempEmail(address=self._address, provider="temp-inbox.me")

    def list_emails(self, address: str) -> List[InboxEmail]:
        self._ensure_session()

        resp = self._session.get(self.BASE_URL, timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')
        result = []

        # Find email table rows
        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:
                subject = cells[0].get_text(strip=True)
                sender = cells[1].get_text(strip=True)
                link = cells[0].find('a')
                email_id = ''
                if link and link.get('href'):
                    email_id = link.get('href', '').split('/')[-1]
                if subject and 'Subject' not in subject and 'No messages' not in subject:
                    result.append(InboxEmail(
                        id=email_id,
                        from_address=sender,
                        subject=subject,
                        date='',
                        body_html='',
                        body_text='',
                        provider="temp-inbox.me",
                        address=address or self._address or "",
                    ))

        return result

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        self._ensure_session()

        resp = self._session.get(f"{self.BASE_URL}/mail/{email_id}", timeout=15)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, 'html.parser')
        content = soup.find('div', {'id': 'mail_content'})
        if not content:
            content = soup.find(class_='email-body')
        body_html = str(content) if content else resp.text

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
            provider="temp-inbox.me",
            address=address or self._address or "",
        )
