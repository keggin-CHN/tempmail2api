"""Guerrilla Mail provider — REST API (api.guerrillamail.com)."""

import logging
import random
import string
from typing import Optional, List

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailGenerateError, EmailFetchError

logger = logging.getLogger("chatgptmail-2api")

# Guerrilla Mail 可用域名
GUERRILLA_DOMAINS = [
    "guerrillamailblock.com",
    "grr.la",
    "guerrillamail.com",
    "guerrillamail.net",
    "guerrillamail.org",
    "sharklasers.com",
    "grr.la",
    "dispostable.com",
]


class GuerrillaMailClient(TempMailClient):
    """Client for Guerrilla Mail API."""

    BASE_URL = "https://api.guerrillamail.com/ajax.php"

    @property
    def provider_name(self) -> str:
        return "guerrillamail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })
        self._sid_token: Optional[str] = None
        self._email_addr: Optional[str] = None

    def _api(self, func: str, **params) -> dict:
        """Call Guerrilla Mail API function."""
        params["f"] = func
        params.setdefault("lang", "en")
        params.setdefault("ip", "127.0.0.1")
        params.setdefault("agent", "Mozilla")
        if self._sid_token:
            params["sid_token"] = self._sid_token
        resp = self._session.get(self.BASE_URL, params=params, timeout=self._timeout)
        resp.raise_for_status()
        return resp.json()

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """Generate a new Guerrilla Mail address."""
        data = self._api("get_email_address")
        self._sid_token = data.get("sid_token", "")
        self._email_addr = data.get("email_addr", "")
        alias = data.get("alias", "")

        if not self._email_addr:
            raise EmailGenerateError("Guerrilla Mail 未返回邮箱地址")

        logger.info("guerrillamail 生成邮箱: %s (alias: %s)", self._email_addr, alias)
        return TempEmail(
            address=self._email_addr,
            provider="guerrillamail",
            raw={"sid_token": self._sid_token, "alias": alias},
        )

    def list_emails(self, address: str) -> List[InboxEmail]:
        """List emails in the Guerrilla Mail inbox."""
        if not self._sid_token:
            # 如果没有 session，先创建一个
            self._api("get_email_address")

        data = self._api("check_email", seq="0")
        emails = data.get("list", [])
        result = []
        for m in emails:
            mail_id = str(m.get("mail_id", ""))
            # 跳过欢迎邮件等系统邮件
            result.append(InboxEmail(
                id=mail_id,
                provider="guerrillamail",
                subject=m.get("mail_subject", ""),
                from_email=m.get("mail_from", ""),
                received_at=str(m.get("mail_timestamp", "")),
            ))
        return result

    def get_email_detail(self, email_id: str) -> Optional[InboxEmail]:
        """Fetch full email content."""
        if not self._sid_token:
            return None
        data = self._api("fetch_email", email_id=email_id)
        if not data or "error" in data:
            return None
        return InboxEmail(
            id=str(data.get("mail_id", email_id)),
            provider="guerrillamail",
            subject=data.get("mail_subject", ""),
            from_email=data.get("mail_from", ""),
            body_html=data.get("mail_body", ""),
            body_text=data.get("mail_text", ""),
            received_at=str(data.get("mail_timestamp", "")),
        )

    def delete_email(self, email_id: str) -> bool:
        """Delete an email."""
        try:
            self._api("del_email", email_id=email_id)
            return True
        except Exception:
            return False
