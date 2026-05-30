"""
Boomlify provider (public API)
API: https://v1.boomlify.com
使用公开的 /emails/public/* 端点，无需认证/验证码
响应使用 XOR 加密
"""

import json
import logging
import random
import string
from typing import Any, Dict, List, Optional

import requests

from .base import InboxEmail, TempEmail, TempMailClient
from .utils import EmailFetchError, EmailGenerateError, retry

logger = logging.getLogger("chatgptmail-2api")

API_BASE = "https://v1.boomlify.com"
ENCRYPTION_KEY = "7a9b3c8d2e1f4g5h6i9j0k8l2m4n6o8p"
TRANSPORT_KEY_RING = {
    "hgjfh": "rk4kA9fQm8v7W4d2TzX1Y",
    "hgjfhg": "t2PzKd9sQw1Lm3XyVbN6R",
    "hihji": "bV7nL2cMzR6eJ8QaHp39T",
    "guyg": "oP6yT1xHaE9qD4KsLi82M",
    "ojigh": "mQ3wN8sRcK5tY2VhUe74Z",
    "igug": "Za1sX9qWe3rT7yUiPl56K",
    "fyv": "Hv4kM2nBq8sR1tJcLz93F",
    "vy": "Qs7nF3bLk1pV8xTdRm64G",
    "gyvg": "Nc5wZ1tQe9yH2rLaKs78D",
    "gjbjb": "Lf8pC6sWd3vX1qTuMz40S",
    "zqplk": "Tx9vK3dRm5nP2sLaQw71E",
    "nmxas": "Rj6mV4qTe8yN1bLcPw53C",
    "rtuwq": "Uw2nZ7sQa4tK9pLeMr86B",
    "bchdk": "Ky3pT5nWv7rQ1mLaZx68A",
    "czmop": "De9fR2sXq5tM1nLbVw84P",
    "kqvtd": "Gk1nP8rTe3yL6mQaZw59J",
    "prxnl": "Bn7qL4tWe2rP9mXsVd61H",
    "svyud": "Hp5mN2qTs8yR1lKaVw73U",
    "tjbqw": "Lm6tQ3nWp9rV2sXeYk45I",
    "wmzlk": "Vb8rP4tQe1mS7nKxZa62O",
    "ydnfc": "Cf2mH7vQp6tN9sLxRw83Y",
    "aejru": "Jq4nT6zWe5rM8vPaLs71X",
    "bpvhs": "Rd3pK9sTe2yN7mQwVb64Z",
    "cltqg": "Wu5sL2nQe8rT1yPaMx93C",
    "pqlmn": "Ep7mV1qRs6tN4xLbYz82D",
    "vtycx": "Ha9tQ2mWe5rP8nXsLv61F",
    "wzufr": "Nk8rS3pTe1yM6wQvZa75G",
    "kdjsh": "Zt4mP7nQw3rS6xLeVy82H",
    "qwert": "Oy6nR5mTe2pL9qXsWa34J",
    "yuiop": "Px1vK8tQe4mN7sLaRw53K",
    "asdfg": "Sm2nL9qTe5rV8pXaZw61M",
    "hklop": "Yd3pM6tQw7nR2sLeVk84N",
}


def _xor_decrypt(encrypted_hex: str, key: str) -> str:
    key_bytes = key.encode("utf-8")
    encrypted_bytes = bytes.fromhex(encrypted_hex)
    decrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(encrypted_bytes))
    return decrypted.decode("utf-8")


def _decrypt_response(data: Any, key_id: Optional[str] = None, key: str = ENCRYPTION_KEY) -> Any:
    if isinstance(data, dict) and "encrypted" in data:
        actual_key = key
        if key_id and key_id in TRANSPORT_KEY_RING:
            actual_key = TRANSPORT_KEY_RING[key_id]
        try:
            decrypted_str = _xor_decrypt(data["encrypted"], actual_key)
            return json.loads(decrypted_str)
        except Exception:
            return data
    return data


class BoomlifyClient(TempMailClient):
    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": "https://boomlify.com",
            "Referer": "https://boomlify.com/",
        })
        self._cached_domains: Optional[List[Dict[str, Any]]] = None

    @property
    def provider_name(self) -> str:
        return "boomlify"

    def _api_request(self, method: str, path: str, **kwargs: Any) -> Any:
        response = self.session.request(method, f"{API_BASE}{path}", timeout=15, **kwargs)
        response.raise_for_status()
        data = response.json()
        enc_key_id = response.headers.get("x-enc-key-id")
        return _decrypt_response(data, key_id=enc_key_id)

    def _get_domains(self) -> List[Dict[str, Any]]:
        if self._cached_domains is None:
            self._cached_domains = self._api_request("GET", "/domains/public")
        return self._cached_domains

    @retry(max_attempts=3, backoff_factor=1.5, exceptions=(requests.RequestException,))
    def generate_email(self, duration_minutes: int = 10, domain: Optional[str] = None) -> TempEmail:
        domains = self._get_domains()
        if not domains:
            raise EmailGenerateError("boomlify 无可用域名")

        if domain:
            target = next((d for d in domains if d["domain"] == domain), None)
            if not target:
                raise ValueError(f"域名 {domain} 不在可用列表中")
        else:
            target = domains[0]

        username = "".join(random.choices(string.ascii_lowercase + string.digits, k=10))
        email_addr = f"{username}@{target['domain']}"

        try:
            data = self._api_request(
                "POST",
                "/emails/public/create",
                json={"email": email_addr, "domainId": target["id"]},
            )
        except requests.RequestException as e:
            raise EmailGenerateError(f"boomlify 创建邮箱失败: {e}") from e

        logger.info("boomlify 生成邮箱: %s", email_addr)
        return TempEmail(
            address=data.get("email", email_addr),
            provider=self.provider_name,
            expires_at=data.get("expires_at"),
            created_at=data.get("created_at"),
            raw=data,
        )

    @retry(max_attempts=3, backoff_factor=1.0, exceptions=(requests.RequestException,))
    def list_emails(self, address: str) -> List[InboxEmail]:
        try:
            data = self._api_request("GET", f"/emails/public/{requests.utils.quote(address, safe='@')}")
        except requests.RequestException as e:
            raise EmailFetchError(f"boomlify 获取收件箱失败: {e}") from e

        emails = data if isinstance(data, list) else []
        return [
            InboxEmail(
                id=str(e.get("id", "")),
                provider=self.provider_name,
                subject=e.get("subject"),
                from_email=e.get("from_email") or (
                    e.get("from", {}).get("address") if isinstance(e.get("from"), dict) else e.get("from")
                ),
                from_name=e.get("from_name") or e.get("fromName"),
                body_html=e.get("body_html") or e.get("html"),
                body_text=e.get("body_text") or e.get("text"),
                received_at=e.get("received_at") or e.get("receivedAt") or e.get("createdAt"),
                raw=e,
            )
            for e in emails
        ]

    @retry(max_attempts=2, backoff_factor=1.0, exceptions=(requests.RequestException,))
    def get_email_detail(self, email_id: str) -> InboxEmail:
        try:
            data = self._api_request("GET", f"/emails/public/{email_id}")
        except requests.RequestException as e:
            raise EmailFetchError(f"boomlify 获取邮件详情失败: {e}") from e

        email_data = data[0] if isinstance(data, list) and data else data
        if isinstance(email_data, list) and not email_data:
            raise EmailFetchError(f"邮件 {email_id} 不存在")

        return InboxEmail(
            id=str(email_data.get("id", email_id)),
            provider=self.provider_name,
            subject=email_data.get("subject"),
            from_email=email_data.get("from_email") or (
                email_data.get("from", {}).get("address") if isinstance(email_data.get("from"), dict) else email_data.get("from")
            ),
            from_name=email_data.get("from_name") or email_data.get("fromName"),
            body_html=email_data.get("body_html") or email_data.get("html"),
            body_text=email_data.get("body_text") or email_data.get("text"),
            received_at=email_data.get("received_at") or email_data.get("receivedAt"),
            raw=data,
        )

    def get_public_domains(self) -> List[Dict[str, Any]]:
        return self._get_domains()
