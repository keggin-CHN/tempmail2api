"""Tempdashmail.org (temp-mail.org web2 API) — clean JWT REST API."""

from typing import List, Optional
from curl_cffi import requests as curl_requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailFetchError


class TempdashmailOrgClient(TempMailClient):
    """Client for https://temp-mail.org/ using web2 API (JWT auth)."""

    BASE_URL = "https://web2.temp-mail.org"

    def __init__(self):
        self._session = curl_requests.Session(impersonate="chrome136")
        self._session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        })
        self._token: Optional[str] = None
        self._address: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "tempdashmail.org"

    def generate_email(self) -> TempEmail:
        resp = self._session.post(f"{self.BASE_URL}/mailbox/", timeout=15)
        resp.raise_for_status()

        data = resp.json()
        self._token = data.get('token', '')
        self._address = data.get('mailbox', '')

        if not self._address or not self._token:
            raise TempMailError("Failed to create mailbox")

        self._session.headers['Authorization'] = f'Bearer {self._token}'
        return TempEmail(address=self._address, provider="tempdashmail.org")

    def list_emails(self, address: str) -> List[InboxEmail]:
        if not self._token:
            raise TempMailError("需要先调用 generate_email")

        resp = self._session.get(f"{self.BASE_URL}/messages/", timeout=15)
        resp.raise_for_status()

        data = resp.json()
        messages = data.get('messages', [])

        result = []
        for msg in messages:
            result.append(InboxEmail(
                id=msg.get('_id', ''),
                from_address=msg.get('from', ''),
                subject=msg.get('subject', ''),
                date=msg.get('receivedAt', ''),
                body_html="",
                body_text=msg.get('bodyPreview', ''),
                provider="tempdashmail.org",
                address=address or self._address or "",
            ))

        return result

    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        if not self._token:
            raise TempMailError("需要先调用 generate_email")

        resp = self._session.get(f"{self.BASE_URL}/messages/{email_id}", timeout=15)
        resp.raise_for_status()

        data = resp.json()
        body_html = data.get('bodyHtml', '')

        return InboxEmail(
            id=email_id,
            from_address=data.get('from', ''),
            subject=data.get('subject', ''),
            date=data.get('receivedAt', ''),
            body_html=body_html,
            body_text="",
            provider="tempdashmail.org",
            address=address or self._address or "",
        )
