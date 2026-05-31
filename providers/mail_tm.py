"""
Mail.tm provider
API: https://api.mail.tm
公开 REST API，无需 API Key，支持完整邮箱生命周期
文档: https://docs.mail.tm
"""

import logging
import random
import string
from typing import Any, Dict, List, Optional

import requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("chatgptmail-2api")

API_BASE = "https://api.mail.tm"


class MailTmClient(TempMailClient):
    """Mail.tm 客户端 — 免费公开 REST API"""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self._token: Optional[str] = None
        self._account_id: Optional[str] = None
        self._cached_domains: Optional[List[str]] = None

    @property
    def provider_name(self) -> str:
        return "mail.tm"

    def _api_request(self, method: str, path: str, auth: bool = False, **kwargs: Any) -> Any:
        """发送 API 请求"""
        headers = {}
        if auth and self._token:
            headers["Authorization"] = f"Bearer {self._token}"

        response = self.session.request(
            method, f"{API_BASE}{path}", headers=headers, timeout=15, **kwargs
        )
        response.raise_for_status()

        if response.status_code == 204:
            return None
        return response.json()

    def _get_domains(self) -> List[str]:
        """获取可用域名列表"""
        if self._cached_domains is None:
            data = self._api_request("GET", "/domains")
            members = data.get("hydra:member", [])
            self._cached_domains = [d["domain"] for d in members if d.get("domain")]
        return self._cached_domains

    @retry(max_attempts=3, backoff_factor=1.5, exceptions=(requests.RequestException,))
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """创建临时邮箱账户"""
        domains = self._get_domains()
        if not domains:
            raise EmailGenerateError("mail.tm 无可用域名")

        target_domain = domain if domain and domain in domains else domains[0]
        username = "".join(random.choices(string.ascii_lowercase + string.digits, k=12))
        address = f"{username}@{target_domain}"
        password = "".join(random.choices(string.ascii_letters + string.digits, k=16))

        try:
            data = self._api_request("POST", "/accounts", json={
                "address": address,
                "password": password,
            })
        except requests.RequestException as e:
            raise EmailGenerateError(f"mail.tm 创建账户失败: {e}") from e

        self._account_id = data.get("id")

        # 获取 JWT token
        try:
            token_data = self._api_request("POST", "/token", json={
                "address": address,
                "password": password,
            })
            self._token = token_data.get("token")
        except requests.RequestException as e:
            raise EmailGenerateError(f"mail.tm 获取 token 失败: {e}") from e

        logger.info("mail.tm 生成邮箱: %s", address)
        return TempEmail(
            address=data.get("address", address),
            provider=self.provider_name,
            created_at=data.get("createdAt"),
            raw=data,
        )

    @retry(max_attempts=3, backoff_factor=1.0, exceptions=(requests.RequestException,))
    def list_emails(self, address: str) -> List[InboxEmail]:
        """获取收件箱列表"""
        if not self._token:
            raise EmailFetchError("请先调用 generate_email()")

        try:
            data = self._api_request("GET", "/messages", auth=True)
        except requests.RequestException as e:
            raise EmailFetchError(f"mail.tm 获取收件箱失败: {e}") from e

        messages = data.get("hydra:member", [])
        return [
            InboxEmail(
                id=str(m.get("id", "")),
                provider=self.provider_name,
                subject=m.get("subject"),
                from_email=m.get("from", {}).get("address") if isinstance(m.get("from"), dict) else None,
                from_name=m.get("from", {}).get("name") if isinstance(m.get("from"), dict) else None,
                body_text=m.get("intro"),
                received_at=m.get("createdAt"),
                raw=m,
            )
            for m in messages
        ]

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(requests.RequestException,))
    def get_email_detail(self, email_id: str) -> InboxEmail:
        """获取邮件详情"""
        if not self._token:
            raise EmailFetchError("请先调用 generate_email()")

        try:
            data = self._api_request("GET", f"/messages/{email_id}", auth=True)
        except requests.RequestException as e:
            raise EmailFetchError(f"mail.tm 获取邮件详情失败: {e}") from e

        html_list = data.get("html", [])
        body_html = html_list[0] if isinstance(html_list, list) and html_list else None

        return InboxEmail(
            id=str(data.get("id", email_id)),
            provider=self.provider_name,
            subject=data.get("subject"),
            from_email=data.get("from", {}).get("address") if isinstance(data.get("from"), dict) else None,
            from_name=data.get("from", {}).get("name") if isinstance(data.get("from"), dict) else None,
            body_html=body_html,
            body_text=data.get("text"),
            received_at=data.get("createdAt"),
            raw=data,
        )

    def delete_email(self, email_id: str) -> bool:
        """删除邮件"""
        if not self._token:
            return False
        try:
            self._api_request("DELETE", f"/messages/{email_id}", auth=True)
            return True
        except Exception:
            return False
