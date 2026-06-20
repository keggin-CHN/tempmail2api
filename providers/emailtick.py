"""
EmailTick provider
API: https://www.emailtick.com
通过 jQuery AJAX 调用后端 HTML 接口，依赖会话 cookie + 隐藏 salt
支持 activate / change / checkmail / delete 全部流程
"""

import logging
import re
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("chatgptmail-2api")

BASE_URL = "https://www.emailtick.com"


class EmailTickClient(TempMailClient):
    """
    EmailTick 临时邮箱客户端

    流程:
    1. GET /  → 解析页面，获取默认 mailbox 和隐藏 salt
    2. POST /index/index/goactive.html → 激活当前地址
    3. POST /index/index/change.html   → 换新地址 / 删除
    4. POST /index/index/checkmail.html → 拉收件箱
    """

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/136.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": BASE_URL + "/",
            "X-Requested-With": "XMLHttpRequest",
        })
        self._mailbox: Optional[str] = None
        self._salt: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "emailtick"

    # ------------------------------------------------------------------
    #  内部工具
    # ------------------------------------------------------------------

    def _fetch_page(self) -> None:
        """GET /，解析默认邮箱地址和隐藏 salt"""
        resp = self.session.get(BASE_URL, timeout=20)
        resp.raise_for_status()

        soup = BeautifulSoup(resp.text, "html.parser")

        # 默认邮箱地址
        mailbox_input = soup.find("input", {"name": "mailbox"})
        if not mailbox_input or not mailbox_input.get("value"):
            raise EmailGenerateError("EmailTick 首页未找到默认邮箱地址")
        self._mailbox = mailbox_input["value"].strip()

        # 隐藏 salt
        salt_input = soup.find("input", {"name": "salt"})
        if not salt_input or not salt_input.get("value"):
            raise EmailGenerateError("EmailTick 首页未找到隐藏 salt")
        self._salt = salt_input["value"].strip()

        logger.info("[emailtick] 页面解析: mailbox=%s, salt=%s", self._mailbox, self._salt[:8])

    def _activate(self, mailbox: str) -> bool:
        """
        POST /index/index/goactive.html
        激活指定邮箱地址，返回 True=成功
        """
        resp = self.session.post(
            f"{BASE_URL}/index/index/goactive.html",
            data={"mailbox": mailbox},
            timeout=15,
        )
        resp.raise_for_status()
        # 返回 "1" 表示成功，其他表示失败
        return resp.text.strip().strip('"') == "1"

    def _parse_emails(self, raw_html: str) -> List[Dict[str, str]]:
        """
        从 checkmail 返回的 HTML 片段解析邮件列表

        HTML 结构:
        <tr>
            <td>sender</td>
            <td><a href='javascript:;' class='detail' data-id='123'>subject</a></td>
            <td>time</td>
        </tr>
        """
        soup = BeautifulSoup(raw_html, "html.parser")
        emails: List[Dict[str, str]] = []

        # 查找带 data-id 的链接（邮件详情链接）
        for link in soup.find_all("a", class_="detail"):
            email_id = link.get("data-id", "")
            subject = link.get_text(strip=True)
            row = link.find_parent("tr")
            sender = ""
            time_str = ""
            if row:
                cells = row.find_all("td")
                if len(cells) >= 1:
                    sender = cells[0].get_text(strip=True)
                if len(cells) >= 3:
                    time_str = cells[2].get_text(strip=True)

            emails.append({
                "id": str(email_id),
                "subject": subject,
                "from_email": sender,
                "received_at": time_str,
            })

        return emails

    # ------------------------------------------------------------------
    #  接口
    # ------------------------------------------------------------------

    @retry(max_attempts=3, backoff_factor=2.0, exceptions=(Exception,))
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """
        获取/生成临时邮箱地址

        EmailTick 的 "生成" 其实是：首次打开页面获取默认地址 → 激活它
        如果要换新地址，可以用 change 接口
        """
        # 首次获取页面信息
        if not self._mailbox or not self._salt:
            self._fetch_page()

        # 激活当前地址
        try:
            ok = self._activate(self._mailbox)
            if not ok:
                logger.warning("[emailtick] 激活 %s 返回失败，尝试换新地址", self._mailbox)
                # 换一个新地址再激活
                resp = self.session.post(
                    f"{BASE_URL}/index/index/change.html",
                    data={"type[]": "1", "set": "1"},
                    timeout=15,
                )
                resp.raise_for_status()
                new_addr = resp.text.strip().strip('"')
                if new_addr == "1" or not new_addr:
                    raise EmailGenerateError(f"EmailTick 换新地址失败: {new_addr}")
                self._mailbox = new_addr
                self._activate(self._mailbox)
        except requests.RequestException as e:
            raise EmailGenerateError(f"EmailTick 激活邮箱失败: {e}") from e

        logger.info("[emailtick] 生成/激活邮箱: %s", self._mailbox)
        return TempEmail(
            address=self._mailbox,
            provider=self.provider_name,
            raw={"salt": self._salt},
        )

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(Exception,))
    def list_emails(self, address: str) -> List[InboxEmail]:
        """
        检查收件箱

        POST /index/index/checkmail.html
        参数: box=邮箱地址, salt=页面隐藏salt
        """
        if not self._salt:
            self._fetch_page()

        try:
            resp = self.session.post(
                f"{BASE_URL}/index/index/checkmail.html",
                data={"box": address, "salt": self._salt},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.RequestException as e:
            raise EmailFetchError(f"EmailTick 检查收件箱失败: {e}") from e

        raw = resp.text.strip()

        # 返回 "2" 表示正在检查中，需要等待
        if raw == "2" or raw == '"2"':
            logger.info("[emailtick] 收件箱正在检查中，返回空列表")
            return []

        # 空结果
        if not raw or raw in ('""', "null", "[]"):
            return []

        # 尝试解析为 JSON（某些情况可能返回 JSON）
        try:
            import json
            data = json.loads(raw)
            if isinstance(data, list):
                return [
                    InboxEmail(
                        id=str(e.get("id", "")),
                        provider=self.provider_name,
                        subject=e.get("subject"),
                        from_email=e.get("from_email") or e.get("from"),
                        body_html=e.get("body_html") or e.get("body"),
                        body_text=e.get("body_text") or e.get("text"),
                        received_at=e.get("received_at") or e.get("time"),
                        raw=e,
                    )
                    for e in data
                ]
        except (json.JSONDecodeError, TypeError):
            pass

        # HTML 解析
        parsed = self._parse_emails(raw)
        return [
            InboxEmail(
                id=e["id"],
                provider=self.provider_name,
                subject=e["subject"],
                from_email=e["from_email"],
                received_at=e["received_at"],
                raw=e,
            )
            for e in parsed
        ]

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(Exception,))
    def get_email_detail(self, email_id: str) -> InboxEmail:
        """
        EmailTick 的邮件详情页面可能需要通过 JS 动态加载。
        这里返回基础信息，body_html 可能需要浏览器渲染。
        """
        # 暂时返回基础信息，详情需要通过 checkmail 的 HTML 来解析
        return InboxEmail(
            id=email_id,
            provider=self.provider_name,
            subject="(EmailTick 邮件详情需要浏览器渲染)",
            body_html=None,
            body_text=None,
            raw={"note": "EmailTick 邮件详情需要浏览器 JS 渲染"},
        )

    def delete_email(self, email_id: str) -> bool:
        """
        删除当前邮箱地址

        POST /index/index/change.html  data-type=2
        """
        if not self._salt:
            self._fetch_page()

        try:
            resp = self.session.post(
                f"{BASE_URL}/index/index/change.html",
                data={"type[]": "2"},
                timeout=15,
            )
            resp.raise_for_status()
            new_addr = resp.text.strip().strip('"')
            # 成功删除后会返回新地址
            if new_addr and new_addr != "1":
                self._mailbox = new_addr
                logger.info("[emailtick] 删除邮箱成功，新地址: %s", new_addr)
                return True
            return False
        except Exception:
            return False
