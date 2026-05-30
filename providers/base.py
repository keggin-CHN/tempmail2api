"""
临时邮箱客户端基类
定义统一接口，所有 provider 必须实现
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class TempEmail:
    """临时邮箱"""
    address: str
    provider: str
    expires_at: Optional[str] = None
    created_at: Optional[str] = None
    duration_minutes: Optional[int] = None
    raw: Dict[str, Any] = field(default_factory=dict)


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


class TempMailClient(ABC):
    """临时邮箱客户端抽象基类"""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """返回 provider 名称"""
        ...

    @abstractmethod
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """
        生成一个临时邮箱地址

        Args:
            duration_minutes: 邮箱有效期（分钟）
            domain: 指定域名（部分 provider 支持）

        Returns:
            TempEmail 对象
        """
        ...

    @abstractmethod
    def list_emails(self, address: str) -> List[InboxEmail]:
        """
        获取收件箱邮件列表

        Args:
            address: 邮箱地址

        Returns:
            InboxEmail 列表
        """
        ...

    @abstractmethod
    def get_email_detail(self, email_id: str) -> InboxEmail:
        """
        获取单封邮件详情

        Args:
            email_id: 邮件 ID

        Returns:
            InboxEmail 对象
        """
        ...

    def delete_email(self, email_id: str) -> bool:
        """
        删除邮件（可选实现）

        Args:
            email_id: 邮件 ID

        Returns:
            是否删除成功
        """
        raise NotImplementedError(f"{self.provider_name} 不支持删除邮件")

    def wait_for_email(
        self,
        address: str,
        timeout: int = 120,
        poll_interval: int = 5,
        since: Optional[str] = None,
    ) -> Optional[InboxEmail]:
        """
        等待新邮件到达

        Args:
            address: 邮箱地址
            timeout: 超时秒数
            poll_interval: 轮询间隔秒数
            since: 只接受此时间之后的邮件

        Returns:
            第一封新邮件，超时返回 None
        """
        import time

        deadline = time.time() + timeout
        while time.time() < deadline:
            emails = self.list_emails(address)
            if since:
                emails = [e for e in emails if (e.received_at or "") > since]
            if emails:
                return emails[0]
            remaining = deadline - time.time()
            if remaining > 0:
                time.sleep(min(poll_interval, remaining))
        return None

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
