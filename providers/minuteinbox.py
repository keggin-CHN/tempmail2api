"""MinuteInbox.com — AJAX + CSRF + JSON API."""

import json
import re
from typing import List, Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailFetchError


class MinuteinboxClient(TempMailClient):
    """Client for https://www.minuteinbox.com/."""

    BASE_URL = "https://www.minuteinbox.com"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self._address: Optional[str] = None
        self._csrf: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "minuteinbox.com"

    def _ensure_session(self):
        if self._address:
            return

        # Get CSRF token
        resp = self._session.get(self.BASE_URL, timeout=15)
        resp.raise_for_status()

        csrf_match = re.search(r'const CSRF="([^"]+)"', resp.text)
        self._csrf = csrf_match.group(1) if csrf_match else ''

        # Set AJAX headers
        self._session.headers.update({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
        })

        # Get email
        resp2 = self._session.get(
            f"{self.BASE_URL}/index/index?csrf_token={self._csrf}",
            timeout=15,
        )
        resp2.raise_for_status()

        try:
            data = json.loads(resp2.content.decode("utf-8-sig"))
            self._address = data.get("email", "")
        except (json.JSONDecodeError, UnicodeDecodeError):
            raise TempMailError("解析邮箱失败")

        if not self._address:
            raise TempMailError("无法创建邮箱")

    def generate_email(self) -> TempEmail:
        self._ensure_session()
        return TempEmail(address=self._address, provider="minuteinbox.com")

    def list_emails(self, address: str) -> List[InboxEmail]:
        self._ensure_session()

        resp = self._session.get(self.BASE_URL, timeout=15)
        resp.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        result = []

        for row in soup.find_all('tr'):
            cells = row.find_all('td')
            if len(cells) >= 3:
                subject = cells[0].get_text(strip=True)
                sender = cells[1].get_text(strip=True)
                link = cells[0].find('a')
                email_id = ''
                if link and link.get('href'):
                    email_id = link.get('href', '').split('/')[-1]
                if subject and 'Subject' not in subject:
                    result.append(InboxEmail(
                        id=email_id,
                        from_address=sender,
                        subject=subject,
                        date='',
                        body_html='',
                        body_text='',
                        provider="minuteinbox.com",
                        address=address or self._address or "",
                    ))

        return result

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        self._ensure_session()

        resp = self._session.get(
            f"{self.BASE_URL}/email/id/{email_id}", timeout=15
        )
        resp.raise_for_status()

        body_html = resp.text
        if '\n' in body_html:
            body_html = body_html.split('\n', 1)[1]

        return InboxEmail(
            id=email_id,
            from_address='',
            subject='',
            date='',
            body_html=body_html,
            body_text='',
            provider="minuteinbox.com",
            address=address or self._address or "",
        )
