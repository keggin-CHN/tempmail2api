"""Tempemail.co provider — REST API + BeautifulSoup."""

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


class TempemailCoClient(TempMailClient):
    """Client for https://tempemail.co/"""

    BASE_URL = "https://tempemail.co"

    @property
    def provider_name(self) -> str:
        return "tempemail.co"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()

    def _get_domains(self) -> list:
        if BeautifulSoup is None:
            return ["tempemail.co"]
        resp = self._session.get(self.BASE_URL, timeout=self._timeout)
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            select = soup.find("select", {"id": "email_domain"})
            if select:
                return [opt["value"] for opt in select.find_all("option") if opt.get("value")]
        return ["tempemail.co"]

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        if not domains:
            raise TempMailError("No domains available")
        selected = domain if domain and domain in domains else domains[0]
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
        return TempEmail(address=f"{name}@{selected}", provider="tempemail.co")

    def list_emails(self, address: str) -> list:
        if BeautifulSoup is None:
            raise TempMailError("beautifulsoup4 required")
        name, domain = address.split("@", 1)
        resp = self._session.get(
            f"{self.BASE_URL}/get-mails",
            params={"mail_id": f"{name}@{domain}", "unseen": 0, "is_new": 1},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            soup = BeautifulSoup(data.get("mails", ""), "html.parser")
            tbody = soup.find("tbody", {"id": "append_email"})
            if not tbody:
                return []
            result = []
            for tr in tbody.find_all("tr"):
                try:
                    a = tr.find("a")
                    eid = a.get("data-id", "") if a else ""
                    sender = tr.find("span", {"class": "rhide"})
                    subj_td = tr.find("td", {"class": "rsubject rhide"})
                    time_td = tr.find("td", {"class": "rtime"})
                    result.append(InboxEmail(
                        id=eid,
                        provider="tempemail.co",
                        from_email=sender.text.strip() if sender else "unknown",
                        subject=subj_td.a.p.text.strip() if subj_td and subj_td.a and subj_td.a.p else "(no subject)",
                        received_at=time_td.a.span.text.strip() if time_td and time_td.a and time_td.a.span else "",
                    ))
                except Exception:
                    continue
            return result
        return []

    def get_email_detail(self, address: str, email_id: str) -> Optional[InboxEmail]:
        resp = self._session.get(
            f"{self.BASE_URL}/mail/info",
            params={"id": email_id},
            timeout=self._timeout,
        )
        if resp.status_code == 200:
            data = resp.json()
            mail = data.get("mail", {})
            return InboxEmail(
                id=email_id,
                provider="tempemail.co",
                from_email=mail.get("from", "unknown"),
                subject=mail.get("subject", "(no subject)"),
                received_at=str(mail.get("date", "")),
                body_html=mail.get("textHtml", ""),
            )
        return None
