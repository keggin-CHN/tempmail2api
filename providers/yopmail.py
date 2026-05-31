"""
Yopmail provider
API: https://yopmail.com
传统 Web 应用，使用 yp/yj 参数 + HTML 解析
"""

import logging
import random
import re
import string
from typing import Any, Dict, List, Optional

import requests
from bs4 import BeautifulSoup

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("chatgptmail-2api")

BASE_URL = "https://yopmail.com"


class YopmailClient(TempMailClient):
    """Yopmail 客户端 — 免费公开临时邮箱，无需注册"""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:136.0) Gecko/20100101 Firefox/136.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        })
        self._username: Optional[str] = None
        self._yp: Optional[str] = None
        self._yj: Optional[str] = None
        self._version: str = "9.0"

    @property
    def provider_name(self) -> str:
        return "yopmail"

    def _init_session(self) -> None:
        """初始化 yopmail 参数 (yp, yj, version)"""
        r = self.session.get(f"{BASE_URL}/en/", timeout=15)
        r.raise_for_status()

        # 提取 version
        ver_match = re.search(r'/ver/([0-9.]+)/webmail\.js', r.text)
        if ver_match:
            self._version = ver_match.group(1)

        # 提取 yp
        soup = BeautifulSoup(r.text, "html.parser")
        yp_el = soup.find("input", {"name": "yp", "id": "yp"})
        if yp_el:
            self._yp = yp_el.get("value", "")

        # 提取 yj
        r2 = self.session.get(f"{BASE_URL}/ver/{self._version}/webmail.js", timeout=15)
        yj_match = re.search(r"value\+'&yj=([0-9a-zA-Z]+)&v='", r2.text)
        if yj_match:
            self._yj = yj_match.group(1)

    @retry(max_attempts=3, backoff_factor=1.5, exceptions=(requests.RequestException,))
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        """生成随机 yopmail 邮箱地址"""
        self._init_session()

        username = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
        self._username = username
        address = f"{username}@yopmail.com"

        logger.info("yopmail 生成邮箱: %s", address)
        return TempEmail(
            address=address,
            provider=self.provider_name,
            raw={"username": username, "yp": self._yp, "yj": self._yj, "version": self._version},
        )

    def _set_ytime(self) -> None:
        """设置 ytime cookie"""
        import datetime
        now = datetime.datetime.now().time()
        ytime = f"{now.hour}:{now.minute}"
        self.session.cookies.set("ytime", ytime, domain="yopmail.com", path="/")

    def _get_inbox_page(self, page: int = 1) -> str:
        """获取收件箱 HTML"""
        if not self._yp or not self._yj:
            self._init_session()
        self._set_ytime()

        params = {
            "login": self._username,
            "p": str(page),
            "d": "",
            "ctrl": "",
            "yp": self._yp,
            "yj": self._yj,
            "v": self._version,
            "r_c": "",
            "id": "",
            "ad": "0",
        }
        r = self.session.get(f"{BASE_URL}/en/inbox", params=params, timeout=15)
        r.raise_for_status()
        return r.text

    @retry(max_attempts=3, backoff_factor=1.0, exceptions=(requests.RequestException,))
    def list_emails(self, address: str) -> List[InboxEmail]:
        """获取收件箱列表"""
        username = address.split("@")[0]
        self._username = username

        try:
            html = self._get_inbox_page()
        except Exception as e:
            raise EmailFetchError(f"yopmail 获取收件箱失败: {e}") from e

        soup = BeautifulSoup(html, "html.parser")
        emails = []

        for mail_div in soup.find_all("div", {"class": "m"}):
            mail_id = mail_div.get("id", "")
            if not mail_id:
                continue

            # 提取发件人
            from_el = mail_div.find("span", {"class": "lmfrom"})
            from_email = from_el.get_text(strip=True) if from_el else None

            # 提取主题
            subject_el = mail_div.find("span", {"class": "lms"})
            subject = subject_el.get_text(strip=True) if subject_el else None

            # 提取时间
            time_el = mail_div.find("span", {"class": "lmh"})
            time_str = time_el.get_text(strip=True) if time_el else None

            emails.append(InboxEmail(
                id=str(mail_id),
                provider=self.provider_name,
                subject=subject,
                from_email=from_email,
                received_at=time_str,
                raw={"mail_id": mail_id},
            ))

        return emails

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(requests.RequestException,))
    def get_email_detail(self, email_id: str) -> InboxEmail:
        """获取邮件详情"""
        if not self._yp or not self._yj:
            self._init_session()
        self._set_ytime()

        params = {
            "b": self._username,
            "id": f"m{email_id}",
        }
        r = self.session.get(f"{BASE_URL}/en/mail", params=params, timeout=15)
        r.raise_for_status()

        soup = BeautifulSoup(r.text, "html.parser")
        mail_div = soup.find("div", {"id": "mail"})

        # 提取发件人
        from_el = soup.find("span", {"id": "msgfrom"})
        from_email = from_el.get_text(strip=True) if from_el else None

        # 提取主题
        subject_el = soup.find("span", {"id": "msgsubject"})
        subject = subject_el.get_text(strip=True) if subject_el else None

        # 提取时间
        time_el = soup.find("span", {"id": "msgdate"})
        time_str = time_el.get_text(strip=True) if time_el else None

        # 提取正文
        body_html = str(mail_div) if mail_div else None
        body_text = mail_div.get_text(strip=True) if mail_div else None

        return InboxEmail(
            id=email_id,
            provider=self.provider_name,
            subject=subject,
            from_email=from_email,
            body_html=body_html,
            body_text=body_text,
            received_at=time_str,
            raw={"mail_id": email_id},
        )
