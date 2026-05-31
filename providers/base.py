"""
临时邮箱客户端基类
定义统一接口，所有 provider 必须实现
"""

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("chatgptmail-2api")


@dataclass
class TempEmail:
    """临时邮箱"""
    address: str
    provider: str
    expires_at: Optional[str] = None
    created_at: Optional[str] = None
    duration_minutes: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"{self.address} ({self.provider})"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "address": self.address,
            "provider": self.provider,
            "expires_at": self.expires_at,
            "created_at": self.created_at,
            "duration_minutes": self.duration_minutes,
        }


@dataclass
class InboxEmail:
    """收件箱中的邮件"""
    id: str
    provider: str
    subject: Optional[str] = None
    from_email: Optional[str] = None
    from_name: Optional[str] = None
    body_html: Optional[str] = None
    body_text: Optional[str] = None
    received_at: Optional[str] = None
    raw: Dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        sender = self.from_name or self.from_email or "未知"
        return f"[{self.provider}] {self.subject or '(无主题)'} - {sender}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "provider": self.provider,
            "subject": self.subject,
            "from_email": self.from_email,
            "from_name": self.from_name,
            "body_html": self.body_html,
            "body_text": self.body_text,
            "received_at": self.received_at,
        }


class TempMailClient(ABC):
    """临时邮箱客户端抽象基类"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...

    @abstractmethod
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        ...

    @abstractmethod
    def list_emails(self, address: str) -> List[InboxEmail]:
        ...

    @abstractmethod
    def get_email_detail(self, email_id: str) -> InboxEmail:
        ...

    def delete_email(self, email_id: str) -> bool:
        raise NotImplementedError(f"{self.provider_name} 不支持删除邮件")

    # ------------------------------------------------------------------
    #  等待 & 轮询
    # ------------------------------------------------------------------

    def wait_for_email(
        self,
        address: str,
        timeout: int = 120,
        poll_interval: int = 5,
        since: Optional[str] = None,
        on_poll: Optional[Callable[[int, int], None]] = None,
    ) -> Optional[InboxEmail]:
        """
        轮询等待新邮件到达

        Args:
            address:       邮箱地址
            timeout:       超时秒数（默认 120）
            poll_interval: 轮询间隔秒数（默认 5）
            since:         只接受此时间之后的邮件
            on_poll:       每次轮询的回调 (attempt, remaining_seconds)

        Returns:
            第一封新邮件，超时返回 None
        """
        deadline = time.time() + timeout
        attempt = 0
        # 自适应间隔：前 30s 用较短间隔（2s），之后用 poll_interval
        adaptive_fast = 2
        adaptive_fast_until = time.time() + 30

        logger.info(
            "[%s] 等待邮件 %s (超时 %ds, 间隔 %ds)",
            self.provider_name, address, timeout, poll_interval,
        )

        while time.time() < deadline:
            attempt += 1
            remaining = deadline - time.time()

            try:
                emails = self.list_emails(address)
            except Exception as e:
                logger.warning("[%s] 第 %d 次轮询出错: %s", self.provider_name, attempt, e)
                # 网络错误时不立即放弃，等下一个周期
                sleep_time = min(poll_interval, remaining)
                if sleep_time > 0:
                    time.sleep(sleep_time)
                continue

            if since:
                emails = [e for e in emails if (e.received_at or "") > since]

            if emails:
                logger.info(
                    "[%s] 第 %d 次轮询收到 %d 封邮件",
                    self.provider_name, attempt, len(emails),
                )
                return emails[0]

            if on_poll:
                on_poll(attempt, int(remaining))

            # 自适应间隔
            interval = adaptive_fast if time.time() < adaptive_fast_until else poll_interval
            sleep_time = min(interval, remaining)
            if sleep_time > 0:
                time.sleep(sleep_time)

        logger.warning("[%s] 等待超时 %ds，未收到邮件", self.provider_name, timeout)
        return None

    def wait_for_emails(
        self,
        address: str,
        count: int = 1,
        timeout: int = 120,
        poll_interval: int = 5,
        since: Optional[str] = None,
    ) -> List[InboxEmail]:
        """
        等待至少 count 封邮件到达

        Returns:
            收到的邮件列表（可能多于 count）
        """
        deadline = time.time() + timeout
        while time.time() < deadline:
            emails = self.list_emails(address)
            if since:
                emails = [e for e in emails if (e.received_at or "") > since]
            if len(emails) >= count:
                return emails
            remaining = deadline - time.time()
            if remaining > 0:
                time.sleep(min(poll_interval, remaining))
        return []

    def generate_and_wait(
        self,
        duration_minutes: int = 10,
        domain: Optional[str] = None,
        timeout: int = 120,
        poll_interval: int = 5,
    ) -> tuple["TempEmail", Optional[InboxEmail]]:
        """
        生成邮箱并等待第一封邮件

        Returns:
            (TempEmail, InboxEmail 或 None)
        """
        email = self.generate_email(duration_minutes=duration_minutes, domain=domain)
        received = self.wait_for_email(email.address, timeout=timeout, poll_interval=poll_interval)
        return email, received
