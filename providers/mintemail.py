"""MintEmail.com provider — simple REST API."""

import random
import string
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError


class MintemailClient(TempMailClient):
    """Client for https://www.mintemail.com/"""

    @property
    def provider_name(self) -> str:
        return "mintemail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@cj.MintEmail.com"
        return TempEmail(address=address, provider="mintemail")

    def list_emails(self, address: str) -> list:
        name, domain = address.split("@", 1)
        resp = self._session.get(
            f"https://www.mintemail.com/m/src/checkemail.php",
            params={"email": name, "domain": domain},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            text = resp.text.strip()
            if text == " " or not text:
                return []
            ids = text[1:].split(",") if text.startswith(",") else text.split(",")
            result = []
            for eid in ids:
                eid = eid.strip()
                if eid:
                    result.append(InboxEmail(
                        id=eid,
                        provider="mintemail",
                        from_email="unknown",
                        subject="(check detail)",
                    ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        name, domain = address.split("@", 1)
        # Get email metadata
        resp = self._session.get(
            f"https://www.mintemail.com/m/src/email.php",
            params={"id": email_id, "email": name, "domain": domain},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            if data:
                m = data[0]
                # Get HTML content
                html_resp = self._session.get(
                    f"https://www.mintemail.com/m/src/emailHtml.php",
                    params={"id": email_id, "email": name, "domain": domain},
                    timeout=self._timeout,
                )
                html = html_resp.text if html_resp.status_code == 200 else ""
                return InboxEmail(
                    id=email_id,
                    provider="mintemail",
                    from_email=m.get("from", "unknown").strip("<>'\""),
                    subject=m.get("subject", "(no subject)"),
                    received_at=str(m.get("date", "")),
                    body_html=html,
                )
        return None
