"""Eyepaste.com provider — RSS feed for inbox."""

import random
import string
from typing import Optional
from xml.etree import ElementTree as ET

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError

try:
    from bs4 import BeautifulSoup
except ImportError:
    BeautifulSoup = None


class EyepasteClient(TempMailClient):
    """Client for https://www.eyepaste.com/"""

    BASE_URL = "https://www.eyepaste.com"

    @property
    def provider_name(self) -> str:
        return "eyepaste"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        address = f"{name}@eyepaste.com"
        return TempEmail(address=address, provider="eyepaste")

    def list_emails(self, address: str) -> list:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.get(f"{self.BASE_URL}/inbox/{address}.rss", timeout=self._timeout)
        if resp.status_code == 200:
            try:
                root = ET.fromstring(resp.text)
                items = root.find("channel").findall("item")
                result = []
                for i, item in enumerate(items):
                    desc = item.find("description")
                    if desc is not None and desc.text:
                        soup = BeautifulSoup(desc.text, "html.parser")
                        paragraphs = soup.find_all("p", limit=2)
                        if paragraphs:
                            info_text = paragraphs[0].text
                            from_email = "unknown"
                            subject = "(no subject)"
                            time_str = ""
                            if " From: " in info_text:
                                parts = info_text.split(" From: ", 1)
                                rest = parts[1]
                                if " To: " in rest:
                                    from_email, rest = rest.split(" To: ", 1)
                                    from_email = from_email.strip()
                                if " Subject: " in rest:
                                    rest2 = rest.split(" Subject: ", 1)[1]
                                    if " Date: " in rest2:
                                        subject, time_str = rest2.split(" Date: ", 1)
                                        subject = subject.strip()
                                        time_str = time_str.strip().rsplit(" ", 1)[0]
                            result.append(InboxEmail(
                                id=str(i),
                                provider="eyepaste",
                                from_email=from_email,
                                subject=subject,
                                received_at=time_str,
                            ))
                return result
            except Exception:
                return []
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        resp = self._session.get(f"{self.BASE_URL}/inbox/{address}.rss", timeout=self._timeout)
        if resp.status_code == 200:
            try:
                root = ET.fromstring(resp.text)
                items = root.find("channel").findall("item")
                idx = int(email_id)
                if 0 <= idx < len(items):
                    desc = items[idx].find("description")
                    if desc is not None and desc.text:
                        soup = BeautifulSoup(desc.text, "html.parser")
                        paragraphs = soup.find_all("p", limit=2)
                        content = ""
                        if len(paragraphs) > 1:
                            content = " ".join(str(s) for s in paragraphs[1].find_next_siblings())
                        elif desc.text:
                            content = desc.text
                        return InboxEmail(id=email_id, provider="eyepaste", body_html=content)
            except Exception:
                pass
        return None
