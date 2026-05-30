"""
TempMail.ing provider
API: https://api.tempmail.ing
Cloudflare Worker 后端，无需认证，支持 ETag 缓存
"""

import logging
from typing import Any, Dict, List, Optional

import requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import ETagCache, EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("chatgptmail-2api")

API_BASE = "https://api.tempmail.ing"


class TempMailIngClient(TempMailClient):
    def __init__(self, etag_ttl: int = 300) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
        })
        self._etag_cache = ETagCache(ttl_seconds=etag_ttl)

    @property
    def provider_name(self) -> str:
        return "tempmail.ing"

    @retry(max_attempts=3, backoff_factor=1.5, exceptions=(requests.RequestException,))
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """
        生成临时邮箱
        duration_minutes: 5/10/15/20/30/60
        """
        try:
            response = self.session.post(
                f"{API_BASE}/api/generate",
                json={"duration": duration_minutes},
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise EmailGenerateError(f"tempmail.ing 生成邮箱请求失败: {e}") from e

        data = response.json()
        if not data.get("success"):
            raise EmailGenerateError(f"tempmail.ing 返回失败: {data}")

        email_data = data.get("email", {})
        address = email_data.get("address")
        if not address:
            raise EmailGenerateError(f"返回中没有邮箱地址: {data}")

        logger.info("tempmail.ing 生成邮箱: %s (有效期 %d 分钟)", address, duration_minutes)
        return TempEmail(
            address=address,
            provider=self.provider_name,
            expires_at=email_data.get("expiresAt"),
            created_at=email_data.get("createdAt"),
            duration_minutes=email_data.get("durationMinutes"),
            raw=data,
        )

    @retry(max_attempts=3, backoff_factor=1.0, exceptions=(requests.RequestException,))
    def list_emails(self, address: str) -> List[InboxEmail]:
        """
        获取收件箱，支持 ETag 条件请求
        - 304 → 内容未变化 → 返回空列表（节省带宽）
        - 200 → 更新本地 ETag 缓存
        """
        headers: Dict[str, str] = {}
        cached_etag = self._etag_cache.get(address)
        if cached_etag:
            headers["If-None-Match"] = cached_etag
            logger.debug("tempmail.ing ETag 命中，发送 If-None-Match: %s", cached_etag[:20])

        try:
            response = self.session.get(
                f"{API_BASE}/api/emails/{requests.utils.quote(address, safe='@')}",
                headers=headers,
                timeout=15,
            )
        except requests.RequestException as e:
            raise EmailFetchError(f"tempmail.ing 获取收件箱失败: {e}") from e

        # 304 = 内容未变化，直接返回空
        if response.status_code == 304:
            logger.debug("tempmail.ing 304 未变化: %s", address)
            return []

        response.raise_for_status()

        # 更新 ETag 缓存
        etag = response.headers.get("ETag")
        if etag:
            self._etag_cache.put(address, etag)

        data = response.json()
        emails = data.get("emails", [])
        logger.debug("tempmail.ing 收件箱: %s, %d 封邮件", address, len(emails))

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

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(requests.RequestException,))
    def get_email_detail(self, email_id: str) -> InboxEmail:
        """获取单封邮件详情"""
        try:
            response = self.session.get(
                f"{API_BASE}/api/emails/{email_id}",
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise EmailFetchError(f"tempmail.ing 获取邮件详情失败: {e}") from e

        data = response.json()
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
        try:
            response = self.session.delete(
                f"{API_BASE}/api/emails/{email_id}",
                timeout=15,
            )
            return response.status_code in (200, 204)
        except requests.RequestException:
            return False

    def cache_stats(self) -> Dict[str, Any]:
        """返回 ETag 缓存统计"""
        return self._etag_cache.stats()
