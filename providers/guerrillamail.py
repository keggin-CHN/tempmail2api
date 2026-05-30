"""
GuerrillaMail provider
API: https://api.guerrillamail.com/ajax.php
公开 API，无需认证，支持自定义用户名
"""

from typing import Any, Dict, List, Optional

import requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import retry

API_BASE = "https://api.guerrillamail.com/ajax.php"


class GuerrillaMailClient(TempMailClient):
    def __init__(self) -> None:
        self.session = requests.Session()
        self._sid_token: Optional[str] = None
        self._email_addr: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "guerrillamail"

    def _api_get(self, params: Dict[str, Any]) -> Any:
        """发送 GET 请求到 GuerrillaMail API"""
        if self._sid_token and "sid_token" not in params:
            params["sid_token"] = self._sid_token
        params.setdefault("lang", "en")

        response = self.session.get(API_BASE, params=params)
        response.raise_for_status()
        return response.json()

    def _ensure_session(self) -> None:
        """确保已有会话"""
        if self._sid_token:
            return
        data = self._api_get({"f": "get_email_address"})
        self._sid_token = data.get("sid_token")
        self._email_addr = data.get("email_addr")

    @retry(max_attempts=3, backoff_factor=1.0)
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """
        生成临时邮箱

        Args:
            duration_minutes: 忽略（GuerrillaMail 邮箱长期有效）
            domain: 可选域名后缀（如 guerrillamail.com, guerrillamailblock.com 等）
        """
        self._ensure_session()

        if domain:
            # 尝试切换域名
            self._api_get({"f": "set_domain", "domain": domain})

        return TempEmail(
            address=self._email_addr,
            provider=self.provider_name,
            raw={"sid_token": self._sid_token},
        )

    def set_username(self, username: str) -> TempEmail:
        """
        设置自定义用户名

        Args:
            username: 自定义用户名（不含@）

        Returns:
            新的 TempEmail 对象
        """
        self._ensure_session()
        data = self._api_get({
            "f": "set_email_user",
            "email_user": username,
        })

        self._email_addr = data.get("email_addr", self._email_addr)
        return TempEmail(
            address=self._email_addr,
            provider=self.provider_name,
            raw=data,
        )

    @retry(max_attempts=3, backoff_factor=1.0)
    def list_emails(self, address: str) -> List[InboxEmail]:
        """获取收件箱"""
        self._ensure_session()

        data = self._api_get({"f": "check_email", "seq": "0"})
        emails = data.get("list", [])

        return [
            InboxEmail(
                id=str(e.get("mail_id", "")),
                provider=self.provider_name,
                subject=e.get("mail_subject"),
                from_email=e.get("mail_from"),
                from_name=None,
                body_html=None,  # 列表接口不含正文
                body_text=e.get("mail_excerpt"),
                received_at=e.get("mail_date"),
                raw=e,
            )
            for e in emails
            if e.get("mail_id", 0) > 0  # 过滤无效邮件
        ]

    @retry(max_attempts=3, backoff_factor=1.0)
    def get_email_detail(self, email_id: str) -> InboxEmail:
        """获取邮件详情"""
        self._ensure_session()

        data = self._api_get({
            "f": "fetch_email",
            "email_id": email_id,
        })

        return InboxEmail(
            id=str(data.get("mail_id", email_id)),
            provider=self.provider_name,
            subject=data.get("mail_subject"),
            from_email=data.get("mail_from"),
            from_name=None,
            body_html=data.get("mail_body"),
            body_text=data.get("mail_excerpt"),
            received_at=data.get("mail_date"),
            raw=data,
        )

    def delete_email(self, email_id: str) -> bool:
        """删除邮件"""
        self._ensure_session()

        try:
            self._api_get({
                "f": "del_email",
                "email_ids[]": email_id,
            })
            return True
        except Exception:
            return False

    def get_domains(self) -> List[str]:
        """获取可用域名列表"""
        self._ensure_session()
        data = self._api_get({"f": "get_email_list"})
        return [d.get("name", "") for d in data.get("list", []) if d.get("name")]

    def forget_me(self) -> bool:
        """取消关联当前邮箱地址"""
        self._ensure_session()
        try:
            self._api_get({"f": "forget_me"})
            self._sid_token = None
            self._email_addr = None
            return True
        except Exception:
            return False
