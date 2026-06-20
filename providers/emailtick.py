"""
EmailTick provider
API: https://www.emailtick.com
通过 jQuery AJAX 调用后端 HTML 接口，依赖会话 cookie + 隐藏 salt
支持 activate / change / checkmail / delete 生命周期
"""

import hashlib
import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

from bs4 import BeautifulSoup
from curl_cffi import requests as curl_requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("chatgptmail-2api")

BASE_URL = "https://www.emailtick.com"


class EmailTickClient(TempMailClient):
    """
    EmailTick 临时邮箱客户端

    流程:
    1. GET /  → 解析当前 mailbox 和隐藏 salt
    2. POST /index/index/goactive.html → 激活当前地址
    3. POST /index/index/change.html   → 切换/随机/删除当前地址
    4. POST /index/index/checkmail.html → 触发服务器检查 Gmail
    5. GET /  → 从首页邮件表格解析邮件列表/详情
    """

    CHANGE_DOT = "1"
    CHANGE_PLUS = "2"
    CHANGE_GOOGLEMAIL = "3"

    def __init__(self) -> None:
        self.session = curl_requests.Session(impersonate="chrome136")
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
        self._last_html: Optional[str] = None

    @property
    def provider_name(self) -> str:
        return "emailtick"

    # ------------------------------------------------------------------
    #  内部工具
    # ------------------------------------------------------------------

    def _fetch_page(self) -> str:
        """GET /，解析当前邮箱地址和隐藏 salt。"""
        resp = self.session.get(BASE_URL + "/", timeout=20)
        resp.raise_for_status()
        self._last_html = resp.text

        soup = BeautifulSoup(resp.text, "html.parser")

        mailbox_input = soup.find("input", {"name": "mailbox"})
        if not mailbox_input or not mailbox_input.get("value"):
            raise EmailGenerateError("EmailTick 首页未找到邮箱地址")
        self._mailbox = mailbox_input["value"].strip()

        salt_input = soup.find("input", {"name": "salt"})
        if not salt_input or not salt_input.get("value"):
            raise EmailGenerateError("EmailTick 首页未找到隐藏 salt")
        self._salt = salt_input["value"].strip()

        logger.info("[emailtick] 页面解析: mailbox=%s, salt=%s", self._mailbox, self._salt[:8])
        return resp.text

    def _ensure_page_state(self) -> None:
        if not self._mailbox or not self._salt:
            self._fetch_page()

    def _activate(self, mailbox: str) -> bool:
        """POST /index/index/goactive.html，返回 True 表示成功。"""
        resp = self.session.post(
            f"{BASE_URL}/index/index/goactive.html",
            data={"mailbox": mailbox},
            timeout=15,
        )
        resp.raise_for_status()
        return resp.text.strip().strip('"') == "1"

    def _post_change(self, type_values: List[str], set_random: bool = False) -> str:
        """
        POST /index/index/change.html。

        页面 jQuery 传数组，后端可接受 type[]；set=1 表示随机生成。
        成功时返回新邮箱地址，"1" 表示访问过频。
        """
        data: Dict[str, Any] = {"type[]": type_values}
        if set_random:
            data["set"] = "1"

        resp = self.session.post(
            f"{BASE_URL}/index/index/change.html",
            data=data,
            timeout=15,
        )
        resp.raise_for_status()
        value = resp.text.strip().strip('"')
        if value == "1":
            raise EmailGenerateError("EmailTick 访问过于频繁，请稍后再试")
        if not value or "@" not in value:
            raise EmailGenerateError(f"EmailTick 切换邮箱失败: {value!r}")

        self._mailbox = value
        self._last_html = None
        return value

    def _message_id(self, row: Any, subject: str, sender: str, received_at: str, index: int) -> str:
        for element in row.find_all(["a", "button"], recursive=True):
            for attr in ("data-id", "data-mail", "data-key", "data-href", "href"):
                value = element.get(attr)
                if value and not str(value).startswith("javascript"):
                    return str(value)
            for attr in ("data-id", "data-mail", "data-key"):
                value = element.get(attr)
                if value:
                    return str(value)

        raw = f"{sender}\n{subject}\n{received_at}\n{index}".encode("utf-8", "ignore")
        return hashlib.sha1(raw).hexdigest()[:16]

    def _extract_body_from_row(self, row: Any) -> tuple[Optional[str], Optional[str]]:
        body_container = row.find(
            class_=re.compile(r"(body|content|detail|message|mail)", re.I)
        )
        if not body_container:
            body_container = row.find("div", id=re.compile(r"(body|content|detail|message|mail)", re.I))
        if not body_container:
            return None, None

        body_html = str(body_container)
        body_text = body_container.get_text("\n", strip=True)
        return body_html, body_text

    def _parse_emails(self, raw_html: str) -> List[Dict[str, Any]]:
        """从首页或 HTML 片段解析邮件列表。"""
        soup = BeautifulSoup(raw_html, "html.parser")
        emails: List[Dict[str, Any]] = []

        rows = soup.select(".msglist tbody tr") or soup.find_all("tr")
        for index, row in enumerate(rows):
            if row.get("id") == "loading-row":
                continue

            cells = row.find_all("td", recursive=False)
            if len(cells) < 3:
                continue

            sender = cells[0].get_text(" ", strip=True)
            subject = cells[1].get_text(" ", strip=True)
            received_at = cells[2].get_text(" ", strip=True)
            if not sender or not subject:
                continue
            if "adsbygoogle" in row.get_text(" ", strip=True):
                continue

            subject_link = cells[1].find("a")
            href = subject_link.get("href") if subject_link else None
            body_html, body_text = self._extract_body_from_row(row)
            email_id = self._message_id(row, subject, sender, received_at, index)

            emails.append({
                "id": email_id,
                "subject": subject,
                "from_email": sender,
                "received_at": received_at,
                "body_html": body_html,
                "body_text": body_text,
                "href": href,
                "raw_html": str(row),
            })

        return emails

    def _fetch_email_href(self, href: str) -> Optional[InboxEmail]:
        if not href or href.startswith("javascript"):
            return None

        url = urljoin(BASE_URL + "/", href)
        resp = self.session.get(url, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        subject = None
        for selector in ("h1", "h2", ".subject", ".mail-subject"):
            element = soup.select_one(selector)
            if element:
                subject = element.get_text(" ", strip=True)
                break

        body = None
        for selector in (".mail-content", ".message-content", ".content", "article", "body"):
            element = soup.select_one(selector)
            if element:
                body = element
                break

        return InboxEmail(
            id=href,
            provider=self.provider_name,
            subject=subject,
            body_html=str(body) if body else resp.text,
            body_text=body.get_text("\n", strip=True) if body else soup.get_text("\n", strip=True),
            raw={"url": url},
        )

    # ------------------------------------------------------------------
    #  统一 provider 接口
    # ------------------------------------------------------------------

    @retry(max_attempts=3, backoff_factor=2.0, exceptions=(Exception,))
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        self._ensure_page_state()

        try:
            ok = self._activate(self._mailbox or "")
            if not ok:
                logger.warning("[emailtick] 激活 %s 返回失败，尝试随机换新地址", self._mailbox)
                self.change_email(random=True)
                self._activate(self._mailbox or "")
        except curl_requests.RequestException as e:
            raise EmailGenerateError(f"EmailTick 激活邮箱失败: {e}") from e

        logger.info("[emailtick] 生成/激活邮箱: %s", self._mailbox)
        return TempEmail(
            address=self._mailbox or "",
            provider=self.provider_name,
            raw={"salt": self._salt},
        )

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(Exception,))
    def list_emails(self, address: str) -> List[InboxEmail]:
        """
        检查并返回收件箱。

        EmailTick 的 checkmail 只触发服务端同步；邮件列表渲染在随后 GET / 的 HTML 表格里。
        """
        self._ensure_page_state()

        try:
            resp = self.session.post(
                f"{BASE_URL}/index/index/checkmail.html",
                data={"box": address, "salt": self._salt},
                timeout=20,
            )
            resp.raise_for_status()
        except curl_requests.RequestException as e:
            raise EmailFetchError(f"EmailTick 检查收件箱失败: {e}") from e

        raw = resp.text.strip().strip('"')
        if raw == "2":
            logger.info("[emailtick] 收件箱正在检查中")
            return []

        html = self._fetch_page()
        parsed = self._parse_emails(html)
        return [
            InboxEmail(
                id=e["id"],
                provider=self.provider_name,
                subject=e["subject"],
                from_email=e["from_email"],
                body_html=e.get("body_html"),
                body_text=e.get("body_text"),
                received_at=e["received_at"],
                raw=e,
            )
            for e in parsed
        ]

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(Exception,))
    def get_email_detail(self, address: str, email_id: str) -> InboxEmail:
        """查看邮件详情；优先从列表 HTML 中返回内联正文，必要时抓取 href。"""
        emails = self.list_emails(address)
        for email in emails:
            if email.id != email_id:
                continue

            href = email.raw.get("href") if email.raw else None
            if href and not email.body_html:
                fetched = self._fetch_email_href(href)
                if fetched:
                    fetched.id = email.id
                    fetched.subject = fetched.subject or email.subject
                    fetched.from_email = email.from_email
                    fetched.received_at = email.received_at
                    return fetched

            if email.body_html or email.body_text:
                return email

            return InboxEmail(
                id=email.id,
                provider=self.provider_name,
                subject=email.subject,
                from_email=email.from_email,
                received_at=email.received_at,
                body_html=email.raw.get("raw_html") if email.raw else None,
                body_text=email.raw.get("raw_html") if email.raw else None,
                raw=email.raw,
            )

        raise EmailFetchError(f"EmailTick 未找到邮件: {email_id}")

    # ------------------------------------------------------------------
    #  EmailTick 专有生命周期接口
    # ------------------------------------------------------------------

    def change_email(
        self,
        change_type: str = CHANGE_DOT,
        random: bool = False,
        activate: bool = True,
    ) -> TempEmail:
        """
        切换邮箱。

        Args:
            change_type: 1=dot Gmail, 2=plus alias, 3=googlemail.com
            random: True 时对应页面 Random 按钮（带 set=1）
            activate: 切换后是否立刻 goactive
        """
        self._ensure_page_state()
        type_values = [self.CHANGE_DOT, self.CHANGE_PLUS, self.CHANGE_GOOGLEMAIL] if random else [str(change_type)]
        address = self._post_change(type_values, set_random=random)
        self._fetch_page()
        if activate:
            self._activate(address)
        return TempEmail(address=address, provider=self.provider_name, raw={"salt": self._salt})

    def delete_current_mailbox(self) -> TempEmail:
        """
        删除/销毁当前 EmailTick Gmail。

        页面删除按钮实际触发的也是 change.html，且网站会进入新地址激活流程。
        因此这里用“随机切换 + 重新激活”来等价表示删除旧地址并拿到新地址。
        """
        self._ensure_page_state()
        address = self._post_change([self.CHANGE_DOT, self.CHANGE_PLUS, self.CHANGE_GOOGLEMAIL], set_random=True)
        self._activate(address)
        self._fetch_page()
        return TempEmail(address=address, provider=self.provider_name, raw={"salt": self._salt})

    def delete_email(self, email_id: str) -> bool:
        """兼容基类命名：EmailTick 网页公开的是删除当前邮箱，而非删除单封邮件。"""
        self.delete_current_mailbox()
        return True
