"""
TempMail Plus provider
API: https://tempmail.plus/api
免费 REST API，无需 API Key
无需创建邮箱，直接用随机地址查询收件箱
支持域名: mailto.plus, fexpost.com, fexbox.org, mailbox.in.ua,
          rover.info, chitthi.in, fextemp.com, any.pink, merepost.com
"""

import logging
import random
import string
from typing import Any, Dict, List, Optional

import requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("tempmail_plus")

API_BASE = "https://tempmail.plus/api"

DOMAINS = [
    "mailto.plus",
    "fexpost.com",
    "fexbox.org",
    "mailbox.in.ua",
    "rover.info",
    "chitthi.in",
    "fextemp.com",
    "any.pink",
    "merepost.com",
]


class TempMailPlusClient(TempMailClient):
    """TempMail Plus 客户端 — 免费 REST API，无需创建邮箱"""

    @property
    def provider_name(self) -> str:
        return "tempmail_plus"

    def __init__(self) -> None:
        self.session = requests.Session()
        self._address: Optional[str] = None
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        })

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """生成临时邮箱地址（本地随机生成，无需 API 调用）"""
        prefix = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
        dom = domain if domain and domain in DOMAINS else random.choice(DOMAINS)
        address = f"{prefix}@{dom}"

        self._address = address
        logger.info("Generated TempMail Plus email: %s", address)

        return TempEmail(
            address=address,
            provider="tempmail_plus",
            raw={"address": address, "domain": dom},
        )

    @retry(max_attempts=2, backoff_factor=2)
    def list_emails(self, address: str) -> List[InboxEmail]:
        """获取收件箱"""
        params = {
            "email": address,
            "limit": "50",
            "epin": "",
        }
        resp = self.session.get(f"{API_BASE}/mails", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("result"):
            return []

        mail_list = data.get("mail_list", [])
        emails = []
        for msg in mail_list:
            emails.append(InboxEmail(
                id=str(msg.get("mail_id", "")),
                provider="tempmail_plus",
                from_email=msg.get("from_mail", ""),
                subject=msg.get("subject", ""),
                received_at=msg.get("time", ""),
                raw=msg,
            ))
        return emails

    @retry(max_attempts=2)
    def get_email_detail(self, email_id: str) -> InboxEmail:
        """获取邮件详情"""
        if not self._address:
            raise EmailFetchError("请先调用 generate_email()")

        params = {
            "email": self._address,
            "epin": "",
        }
        resp = self.session.get(f"{API_BASE}/mails/{email_id}", params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        if not data.get("result"):
            raise EmailFetchError(f"邮件 {email_id} 未找到")

        return InboxEmail(
            id=str(data.get("mail_id", email_id)),
            provider="tempmail_plus",
            from_email=data.get("from_mail", data.get("from", "")),
            subject=data.get("subject", ""),
            received_at=data.get("date", ""),
            body_text=data.get("text", ""),
            body_html=data.get("html", ""),
            raw=data,
        )
