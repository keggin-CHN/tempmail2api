"""mail.tm provider — REST API (api.mail.tm).

mail.tm 提供完整的 RESTful API:
- GET  /domains        → 可用域名列表
- POST /accounts       → 创建账号 (address, password)
- POST /token          → 获取 JWT token
- GET  /messages       → 收件箱列表 (需 Bearer token)
- GET  /messages/{id}  → 邮件详情
- DELETE /messages/{id} → 删除邮件
"""

import logging
import random
import string
from typing import Optional, List

import requests

from .base import TempMailClient, TempEmail, InboxEmail
from .utils import TempMailError, EmailGenerateError, EmailFetchError

logger = logging.getLogger("chatgptmail-2api")


class MailTmClient(TempMailClient):
    """Client for mail.tm REST API."""

    BASE_URL = "https://api.mail.tm"

    @property
    def provider_name(self) -> str:
        return "mailtm"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        self._timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Content-Type": "application/json",
        })
        self._token: Optional[str] = None
        self._address: Optional[str] = None
        self._password: Optional[str] = None
        self._account_id: Optional[str] = None

    def _get_domains(self) -> List[str]:
        """获取可用域名列表。"""
        resp = self._session.get(f"{self.BASE_URL}/domains", timeout=self._timeout)
        resp.raise_for_status()
        data = resp.json()
        domains = []
        for m in data.get("hydra:member", []):
            if m.get("isActive"):
                domains.append(m["domain"])
        return domains

    def _create_account(self, address: str, password: str) -> dict:
        """创建新账号。"""
        resp = self._session.post(
            f"{self.BASE_URL}/accounts",
            json={"address": address, "password": password},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        return resp.json()

    def _get_token(self, address: str, password: str) -> str:
        """获取 JWT token。"""
        resp = self._session.post(
            f"{self.BASE_URL}/token",
            json={"address": address, "password": password},
            timeout=self._timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return data.get("token", "")

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """生成新的临时邮箱地址。"""
        # 获取可用域名
        domains = self._get_domains()
        if not domains:
            raise EmailGenerateError("mail.tm 无可用域名")

        target_domain = domain if domain and domain in domains else domains[0]

        # 生成随机用户名
        name = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
        address = f"{name}@{target_domain}"
        password = ''.join(random.choices(string.ascii_letters + string.digits + "!@#$%", k=16))

        # 创建账号
        account = self._create_account(address, password)
        self._account_id = account.get("id", "")
        self._address = address
        self._password = password

        # 获取 token
        self._token = self._get_token(address, password)

        logger.info("mail.tm 生成邮箱: %s (id: %s)", address, self._account_id)
        return TempEmail(
            address=address,
            provider="mailtm",
            raw={"account_id": self._account_id, "token": self._token[:20] + "..."},
        )

    def list_emails(self, address: str) -> List[InboxEmail]:
        """列出收件箱中的邮件。"""
        if not self._token:
            # 如果没有 token，尝试用保存的凭据获取
            if self._address and self._password:
                self._token = self._get_token(self._address, self._password)
            else:
                return []

        headers = {"Authorization": f"Bearer {self._token}"}
        resp = self._session.get(
            f"{self.BASE_URL}/messages",
            headers=headers,
            timeout=self._timeout,
        )
        if resp.status_code == 401:
            # Token 过期，重新获取
            if self._address and self._password:
                self._token = self._get_token(self._address, self._password)
                headers = {"Authorization": f"Bearer {self._token}"}
                resp = self._session.get(
                    f"{self.BASE_URL}/messages",
                    headers=headers,
                    timeout=self._timeout,
                )

        if resp.status_code != 200:
            return []

        data = resp.json()
        result = []
        for m in data.get("hydra:member", []):
            from_info = m.get("from", {})
            result.append(InboxEmail(
                id=m.get("id", ""),
                provider="mailtm",
                subject=m.get("subject", ""),
                from_email=from_info.get("address", ""),
                from_name=from_info.get("name", ""),
                received_at=m.get("createdAt", ""),
                raw={"intro": m.get("intro", "")},
            ))
        return result

    def get_email_detail(self, email_id: str) -> Optional[InboxEmail]:
        """获取邮件详情。"""
        if not self._token:
            return None

        headers = {"Authorization": f"Bearer {self._token}"}
        resp = self._session.get(
            f"{self.BASE_URL}/messages/{email_id}",
            headers=headers,
            timeout=self._timeout,
        )
        if resp.status_code != 200:
            return None

        m = resp.json()
        from_info = m.get("from", {})
        return InboxEmail(
            id=m.get("id", email_id),
            provider="mailtm",
            subject=m.get("subject", ""),
            from_email=from_info.get("address", ""),
            from_name=from_info.get("name", ""),
            body_html=m.get("html", [""])[0] if m.get("html") else "",
            body_text=m.get("text", ""),
            received_at=m.get("createdAt", ""),
        )

    def delete_email(self, email_id: str) -> bool:
        """删除邮件。"""
        if not self._token:
            return False
        headers = {"Authorization": f"Bearer {self._token}"}
        resp = self._session.delete(
            f"{self.BASE_URL}/messages/{email_id}",
            headers=headers,
            timeout=self._timeout,
        )
        return resp.status_code in (200, 204)
