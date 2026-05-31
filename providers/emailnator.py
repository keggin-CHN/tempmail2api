"""
Emailnator provider (Gmail dot trick)
API: https://www.emailnator.com
使用 Gmail 可兼容地址（dot trick / plus trick），无需认证
需要浏览器 User-Agent 和 X-Requested-With 头
"""

import logging
import random
import string
from typing import Any, Dict, List, Optional

import requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("chatgptmail-2api")

BASE_URL = "https://www.emailnator.com"


class EmailnatorClient(TempMailClient):
    """Emailnator 客户端 — Gmail dot trick 临时邮箱"""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.5",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/json",
            "Origin": BASE_URL,
            "Referer": f"{BASE_URL}/",
        })
        self._current_email: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "emailnator"

    def _init_session(self) -> None:
        """初始化会话，获取必要的 cookies"""
        try:
            self.session.get(BASE_URL, timeout=15)
        except requests.RequestException:
            pass  # cookies 会自动设置

    @retry(max_attempts=3, backoff_factor=2.0, exceptions=(requests.RequestException,))
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """
        生成临时 Gmail 地址

        Args:
            duration_minutes: 忽略（Gmail 地址长期有效）
            domain: 忽略（固定使用 gmail.com）
        """
        self._init_session()

        # 生成随机 Gmail 用户名
        username = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email_addr = f"{username}@gmail.com"

        try:
            response = self.session.post(
                f"{BASE_URL}/generate-email",
                json={"email": [email_addr]},
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise EmailGenerateError(f"emailnator 生成邮箱失败: {e}") from e

        data = response.json()
        generated = data.get("email", [email_addr])
        if isinstance(generated, list) and generated:
            email_addr = generated[0]

        self._current_email = email_addr
        logger.info("emailnator 生成邮箱: %s", email_addr)
        return TempEmail(
            address=email_addr,
            provider=self.provider_name,
            raw=data,
        )

    @retry(max_attempts=3, backoff_factor=1.0, exceptions=(requests.RequestException,))
    def list_emails(self, address: str) -> List[InboxEmail]:
        """获取收件箱列表"""
        try:
            response = self.session.post(
                f"{BASE_URL}/message-list",
                json={"email": address},
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise EmailFetchError(f"emailnator 获取收件箱失败: {e}") from e

        data = response.json()
        messages = data.get("messageData", [])
        if not isinstance(messages, list):
            messages = []

        return [
            InboxEmail(
                id=str(m.get("messageID", "")),
                provider=self.provider_name,
                subject=m.get("subject"),
                from_email=m.get("from"),
                body_text=m.get("textContent") or m.get("snippet"),
                received_at=m.get("date") or m.get("time"),
                raw=m,
            )
            for m in messages
            if m.get("messageID")  # 过滤空消息
        ]

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(requests.RequestException,))
    def get_email_detail(self, email_id: str) -> InboxEmail:
        """获取邮件详情"""
        try:
            response = self.session.post(
                f"{BASE_URL}/message-list",
                json={"email": self._current_email, "messageID": email_id},
                timeout=15,
            )
            response.raise_for_status()
        except requests.RequestException as e:
            raise EmailFetchError(f"emailnator 获取邮件详情失败: {e}") from e

        data = response.json()
        return InboxEmail(
            id=email_id,
            provider=self.provider_name,
            subject=data.get("subject"),
            from_email=data.get("from"),
            body_html=data.get("htmlContent") or data.get("html"),
            body_text=data.get("textContent") or data.get("text"),
            received_at=data.get("date"),
            raw=data,
        )
