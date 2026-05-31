"""Haribu.net provider — Tempail pattern (HTML scraping)."""

import random
import string
from typing import Optional

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


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


class HaribuClient(TempMailClient):
    """Client for https://haribu.net/"""

    BASE_URL = "https://haribu.net"

    @property
    def provider_name(self) -> str:
        return "haribu"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.get(self.BASE_URL, timeout=self._timeout)
        if resp.status_code != 200:
            raise TempMailError(f"Failed to load page: {resp.status_code}")
        soup = BeautifulSoup(resp.text, "html.parser")
        inp = soup.find("input", {"id": "eposta_adres"})
        if not inp or not inp.get("value"):
            raise TempMailError("Could not find email address on page")
        email = inp["value"]
        return TempEmail(address=email, provider="haribu")

    def list_emails(self, address: str) -> list:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.get(self.BASE_URL, timeout=self._timeout)
        if resp.status_code != 200:
            return []
        soup = BeautifulSoup(resp.text, "html.parser")
        result = []
        for mail in soup.find_all("li", {"class": "mail"}):
            try:
                from_div = mail.find("div", {"class": "gonderen"})
                subj_div = mail.find("div", {"class": "baslik"})
                time_div = mail.find("div", {"class": "zaman"})
                from_email = "unknown"
                if from_div and from_div.span and from_div.span.get("data-cfemail"):
                    from_email = _de_cf_email(from_div.span["data-cfemail"])
                result.append(InboxEmail(
                    id=mail.get("id", ""),
                    provider="haribu",
                    from_email=from_email,
                    subject=subj_div.text.strip() if subj_div else "(no subject)",
                    received_at=time_div.text.strip() if time_div else "",
                ))
            except Exception:
                continue
        return result

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.get(f"{self.BASE_URL}/{email_id}", timeout=self._timeout)
        if resp.status_code != 200:
            return None
        soup = BeautifulSoup(resp.text, "html.parser")
        panel = soup.find("div", {"class": "mail-oku-panel"})
        if panel:
            iframe = panel.find("iframe")
            if iframe and iframe.get("src"):
                r2 = self._session.get(iframe["src"], timeout=self._timeout)
                if r2.status_code == 200:
                    return InboxEmail(id=email_id, provider="haribu", body_html=r2.text)
        return InboxEmail(id=email_id, provider="haribu", body_html=resp.text[:5000])
