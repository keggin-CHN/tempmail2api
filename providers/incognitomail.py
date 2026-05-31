"""Incognitomail.co provider — HMAC-signed REST API."""

import json
import time
import hmac
import hashlib
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError

# HMAC key (from reference implementation, has been static for ~6 months)
_HMAC_KEY = b"2N(PphSU<U*?Uh]pd{4--V"


def _sign_payload(data: dict) -> dict:
    """Sign payload with HMAC-SHA256."""
    data["key"] = hmac.new(
        _HMAC_KEY,
        json.dumps(data, separators=(",", ":")).encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return data


class IncognitomailClient(TempMailClient):
    """Client for https://incognitomail.co/"""

    BASE_URL = "https://api.incognitomail.co"

    @property
    def provider_name(self) -> str:
        return "incognitomail"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._email = ""
        self._token = ""

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        payload = _sign_payload({"ts": int(time.time() * 1000)})
        resp = self._session.post(
            f"{self.BASE_URL}/inbox/v2/create",
            json=payload,
            headers={"content-type": "text/plain;charset=UTF-8"},
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            raise TempMailError(f"Failed to create email: {resp.status_code} {resp.text[:200]}")
        data = resp.json()
        self._email = data.get("id", "")
        self._token = data.get("token", "")
        if not self._email:
            raise TempMailError(f"No email in response: {data}")
        return TempEmail(address=self._email, provider="incognitomail")

    def list_emails(self, address: str) -> list:
        payload = _sign_payload({
            "inboxId": address,
            "inboxToken": self._token,
            "ts": int(time.time() * 1000),
        })
        resp = self._session.post(
            f"{self.BASE_URL}/inbox/v1/list",
            json=payload,
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            result = []
            for i, item in enumerate(data.get("items", [])):
                sender = item.get("sender", {})
                result.append(InboxEmail(
                    id=item.get("messageURL", str(i)),
                    provider="incognitomail",
                    from_email=sender.get("email", "unknown") if isinstance(sender, dict) else str(sender),
                    subject=item.get("subject", "(no subject)"),
                    received_at=str(item.get("date", "")),
                ))
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        """email_id is a full URL to the message."""
        resp = self._session.get(email_id, timeout=self._timeout)
        if resp.status_code == 200:
            data = resp.json()
            return InboxEmail(
                id=email_id,
                provider="incognitomail",
                from_email=data.get("sender", {}).get("email", "unknown") if isinstance(data.get("sender"), dict) else "unknown",
                subject=data.get("subject", "(no subject)"),
                body_html=data.get("html", ""),
                body_text=data.get("text", ""),
                received_at=str(data.get("date", "")),
            )
        return None
