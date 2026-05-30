"""
TempMail.ing provider
API: https://api.tempmail.ing
Cloudflare Worker 后端，无需认证，支持 ETag 缓存
"""

from typing import Any, Dict, List, Optional

import requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import retry

API_BASE = "https://api.tempmail.ing"


class TempMailIngClient(TempMailClient):
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self._etags: Dict[str, str] = {}

    @property
    def provider_name(self) -> str:
        return "tempmail.ing"

    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """
        生成临时邮箱
        duration_minutes: 5/10/15/20/30/60
        """
        payload: Dict[str, Any] = {"duration": duration_minutes}

        response = self.session.post(
            f"{API_BASE}/api/generate",
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            raise RuntimeError(f"生成邮箱失败: {data}")

        email_data = data.get("email", {})
        address = email_data.get("address")
        if not address:
            raise RuntimeError(f"返回中没有邮箱地址: {data}")

        return TempEmail(
            address=address,
            provider=self.provider_name,
            expires_at=email_data.get("expiresAt"),
            created_at=email_data.get("createdAt"),
            duration_minutes=email_data.get("durationMinutes"),
            raw=data,
        )

    def list_emails(self, address: str) -> List[InboxEmail]:
        """获取收件箱，支持 ETag 条件请求"""
        headers: Dict[str, str] = {}
        if address in self._etags:
            headers["If-None-Match"] = self._etags[address]

        response = self.session.get(
            f"{API_BASE}/api/emails/{requests.utils.quote(address, safe='@')}",
            headers=headers,
        )

        # 304 = 内容未变化
        if response.status_code == 304:
            return []

        response.raise_for_status()

        # 更新 ETag
        etag = response.headers.get("ETag")
        if etag:
            self._etags[address] = etag

        data = response.json()
        emails = data.get("emails", [])

        return [
            InboxEmail(
                id=str(e.get("id", e.get("_id", ""))),
                provider=self.provider_name,
                subject=e.get("subject"),
                from_email=e.get("from") if isinstance(e.get("from"), str) else e.get("from", {}).get("address") if isinstance(e.get("from"), dict) else None,
                from_name=e.get("fromName") if "fromName" in e else (e.get("from", {}).get("name") if isinstance(e.get("from"), dict) else None),
                body_html=e.get("html") or e.get("body"),
                body_text=e.get("text"),
                received_at=e.get("createdAt") or e.get("date") or e.get("receivedAt"),
                raw=e,
            )
            for e in emails
        ]

    def get_email_detail(self, email_id: str) -> InboxEmail:
        """获取单封邮件详情"""
        response = self.session.get(
            f"{API_BASE}/api/emails/{email_id}",
        )
        response.raise_for_status()
        data = response.json()

        # API 可能直接返回邮件对象，也可能包在 data 里
        email_data = data.get("data", data)

        return InboxEmail(
            id=str(email_data.get("id", email_data.get("_id", email_id))),
            provider=self.provider_name,
            subject=email_data.get("subject"),
            from_email=email_data.get("from") if isinstance(email_data.get("from"), str) else email_data.get("from", {}).get("address") if isinstance(email_data.get("from"), dict) else None,
            body_html=email_data.get("html") or email_data.get("body"),
            body_text=email_data.get("text"),
            received_at=email_data.get("createdAt") or email_data.get("date"),
            raw=data,
        )

    def delete_email(self, email_id: str) -> bool:
        """删除邮件"""
        response = self.session.delete(
            f"{API_BASE}/api/emails/{email_id}",
        )
        return response.status_code in (200, 204)
