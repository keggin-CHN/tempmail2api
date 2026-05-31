"""
Mohmal provider
API: https://www.mohmal.com
传统 Web 应用，使用 session cookie + HTML 解析
支持创建临时邮箱、查看收件箱、读取邮件详情
"""

import logging
import re
from typing import Any, Dict, List, Optional

from curl_cffi import requests as cffi_requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("chatgptmail-2api")

BASE_URL = "https://www.mohmal.com"


class MohmalClient(TempMailClient):
    """Mohmal 客户端 — 阿拉伯语垃圾邮件的意思，45 分钟有效期"""

    def __init__(self) -> None:
        self.session = cffi_requests.Session(impersonate="chrome136")
        self.session.headers.update({
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self._email: Optional[str] = None
        self._lang: str = "en"

    @property
    def provider_name(self) -> str:
        return "mohmal"

    @retry(max_attempts=3, backoff_factor=2.0, exceptions=(Exception,))
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """创建临时邮箱（随机生成）"""
        try:
            r = self.session.get(
                f"{BASE_URL}/{self._lang}/create/random",
                timeout=15,
                allow_redirects=True,
            )
            r.raise_for_status()
        except Exception as e:
            raise EmailGenerateError(f"mohmal 创建邮箱失败: {e}") from e

        # 从 inbox 页面提取邮箱地址
        email_match = re.search(
            r'class="email[^"]*"[^>]*>([^<]+@[^<]+)</(?:span|div|p)',
            r.text,
        )
        if not email_match:
            email_match = re.search(
                r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})',
                r.text,
            )

        if not email_match:
            raise EmailGenerateError("mohmal 无法从页面提取邮箱地址")

        self._email = email_match.group(1).strip()
        logger.info("mohmal 生成邮箱: %s", self._email)
        return TempEmail(
            address=self._email,
            provider=self.provider_name,
            raw={"cookies": dict(self.session.cookies)},
        )

    def _parse_inbox_page(self, html: str) -> List[InboxEmail]:
        """解析 inbox 页面的 HTML，提取消息列表"""
        emails = []
        # 找所有带 data-msg-id 的 tr 行
        rows = re.findall(
            r'<tr[^>]*data-msg-id="([^"]*)"[^>]*>(.*?)</tr>',
            html,
            re.DOTALL,
        )
        for msg_id, row_html in rows:
            # 提取 subject, time, sender
            cells = re.findall(r'<td[^>]*>(.*?)</td>', row_html, re.DOTALL)
            subject = re.sub(r'<[^>]+>', '', cells[0]).strip() if len(cells) > 0 else None
            time_str = re.sub(r'<[^>]+>', '', cells[1]).strip() if len(cells) > 1 else None
            sender = re.sub(r'<[^>]+>', '', cells[2]).strip() if len(cells) > 2 else None

            emails.append(InboxEmail(
                id=msg_id,
                provider=self.provider_name,
                subject=subject,
                from_email=sender,
                received_at=time_str,
                raw={"msg_id": msg_id},
            ))
        return emails

    @retry(max_attempts=3, backoff_factor=1.5, exceptions=(Exception,))
    def list_emails(self, address: str) -> List[InboxEmail]:
        """获取收件箱列表"""
        try:
            r = self.session.get(
                f"{BASE_URL}/{self._lang}/inbox",
                timeout=15,
            )
            r.raise_for_status()
        except Exception as e:
            raise EmailFetchError(f"mohmal 获取收件箱失败: {e}") from e

        return self._parse_inbox_page(r.text)

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(Exception,))
    def get_email_detail(self, email_id: str) -> InboxEmail:
        """获取邮件详情（通过 iframe 加载）"""
        try:
            r = self.session.get(
                f"{BASE_URL}/{self._lang}/message/{email_id}",
                timeout=15,
            )
            r.raise_for_status()
        except Exception as e:
            raise EmailFetchError(f"mohmal 获取邮件详情失败: {e}") from e

        # 解析邮件内容
        html = r.text

        # 提取 subject
        subject_match = re.search(r'class="subject"[^>]*>([^<]+)<', html)
        subject = subject_match.group(1).strip() if subject_match else None

        # 提取 sender
        sender_match = re.search(r'class="sender"[^>]*>.*?class="value"[^>]*>([^<]+)<', html, re.DOTALL)
        sender = sender_match.group(1).strip() if sender_match else None

        # 提取 time
        time_match = re.search(r'class="time"[^>]*>.*?class="value"[^>]*>([^<]+)<', html, re.DOTALL)
        time_str = time_match.group(1).strip() if time_match else None

        # 提取 body (iframe src)
        iframe_match = re.search(r'<iframe[^>]*src="([^"]*)"', html)
        body_html = None
        if iframe_match:
            iframe_src = iframe_match.group(1)
            if iframe_src.startswith('/'):
                iframe_src = f"{BASE_URL}{iframe_src}"
            try:
                r2 = self.session.get(iframe_src, timeout=10)
                body_html = r2.text
            except Exception:
                pass

        # 提取纯文本
        body_text = re.sub(r'<[^>]+>', '', body_html).strip() if body_html else None

        return InboxEmail(
            id=email_id,
            provider=self.provider_name,
            subject=subject,
            from_email=sender,
            body_html=body_html,
            body_text=body_text,
            received_at=time_str,
            raw={"msg_id": email_id},
        )
