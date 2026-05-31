"""ExpressInboxHub.com — CSRF + REST API (_Fake_trash_mail pattern)."""

from typing import List, Optional

import requests
from bs4 import BeautifulSoup

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailFetchError


class ExpressinboxhubClient(TempMailClient):
    """Client for https://expressinboxhub.com/."""

    BASE_URL = "https://expressinboxhub.com"

    def __init__(self):
        self._session = requests.Session()
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self._token: Optional[str] = None
        self._address: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "expressinboxhub"

    def _ensure_session(self):
        if self._token:
            return

        resp = self._session.get(self.BASE_URL, timeout=15)
        resp.raise_for_status()

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        csrf = soup.find('meta', {'name': 'csrf-token'})
        if not csrf:
            raise TempMailError("无法获取 CSRF token")

        self._token = csrf.get('content', '')
        self._session.headers.update({
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json',
        })

        resp2 = self._session.post(f"{self.BASE_URL}/messages", data={
            '_token': self._token,
        }, timeout=15)
        resp2.raise_for_status()

        data = resp2.json()
        self._address = data.get('mailbox', '')
        if not self._address:
            raise TempMailError("无法创建邮箱")

    def generate_email(self) -> TempEmail:
        self._ensure_session()
        return TempEmail(address=self._address, provider="expressinboxhub")

    def list_emails(self, address: str) -> List[InboxEmail]:
        self._ensure_session()

        resp = self._session.post(f"{self.BASE_URL}/messages", data={
            '_token': self._token,
        }, timeout=15)
        resp.raise_for_status()

        data = resp.json()
        messages = data.get('messages', [])

        result = []
        for msg in messages:
            body = msg.get('content', '')
            result.append(InboxEmail(
                id=msg.get('id', ''),
                from_address=msg.get('from', ''),
                subject=msg.get('subject', ''),
                date=msg.get('receivedAt', ''),
                body_html=body if '<' in body else '',
                body_text='' if '<' in body else body,
                provider="expressinboxhub",
                address=address or self._address or "",
            ))

        return result

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        emails = self.list_emails(address)
        for email in emails:
            if email.id == email_id:
                return email

        raise TempMailError(f"邮件 {email_id} 未找到")
