import json
import re
import time
from typing import Any, Dict, List, Optional, Tuple

import requests
from curl_cffi import requests as curl_requests


CHATGPTMAIL_BASE_URL = "https://mail.chatgpt.org.uk"
RESEND_API_BASE_URL = "https://api.resend.com"

# 你提供的测试配置
RESEND_API_KEY = ""
SENDER_EMAIL = ""

# SMTP 信息保留在这里做记录；本脚本默认优先走 Resend HTTP API
SMTP_SERVER = "smtp.resend.com"
SMTP_PORT = 465
SMTP_USERNAME = "resend"

# 测试参数
POLL_INTERVAL_SECONDS = 5
POLL_TIMEOUT_SECONDS = 120


class ChatGPTMailClient:
    def __init__(self) -> None:
        self.session = curl_requests.Session(impersonate="chrome136")

    def get_initial_token(self) -> str:
        response = self.session.get(CHATGPTMAIL_BASE_URL)
        response.raise_for_status()

        match = re.search(r"window\.__BROWSER_AUTH\s*=\s*({[^}]+})", response.text)
        if not match:
            raise RuntimeError("未能从首页提取 window.__BROWSER_AUTH")

        auth_data = json.loads(match.group(1))
        token = auth_data.get("token")
        if not token:
            raise RuntimeError("首页鉴权数据中不存在 token")

        return token

    def generate_email(self, domain: Optional[str] = None) -> Tuple[str, str, Dict[str, Any]]:
        initial_token = self.get_initial_token()

        headers = {
            "X-Inbox-Token": initial_token,
            "Content-Type": "application/json",
        }

        payload: Dict[str, Any] = {}
        if domain:
            payload["domain"] = domain

        response = self.session.post(
            f"{CHATGPTMAIL_BASE_URL}/api/generate-email",
            headers=headers,
            json=payload,
        )
        response.raise_for_status()
        data = response.json()

        if not data.get("success"):
            raise RuntimeError(f"生成邮箱失败: {data}")

        email = data.get("data", {}).get("email")
        inbox_token = data.get("auth", {}).get("token")

        if not email or not inbox_token:
            raise RuntimeError(f"返回结果缺少 email 或 auth.token: {data}")

        return email, inbox_token, data

    def list_emails(self, email: str, inbox_token: str) -> Dict[str, Any]:
        headers = {
            "X-Inbox-Token": inbox_token,
        }

        response = self.session.get(
            f"{CHATGPTMAIL_BASE_URL}/api/emails",
            params={"email": email},
            headers=headers,
        )
        response.raise_for_status()
        return response.json()

    def get_email_detail(self, email_id: str, inbox_token: str) -> Dict[str, Any]:
        headers = {
            "X-Inbox-Token": inbox_token,
        }

        response = self.session.get(
            f"{CHATGPTMAIL_BASE_URL}/api/email/{email_id}",
            headers=headers,
        )
        response.raise_for_status()
        return response.json()


def send_test_email_via_resend_api(
    api_key: str,
    from_email: str,
    to_email: str,
    subject: str,
    html: str,
    text: str,
) -> Dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": subject,
        "html": html,
        "text": text,
    }

    response = requests.post(
        f"{RESEND_API_BASE_URL}/emails",
        headers=headers,
        json=payload,
        timeout=30,
    )

    try:
        data = response.json()
    except Exception:
        data = {"raw_text": response.text}

    if response.status_code >= 400:
        raise RuntimeError(f"Resend 发信失败: status={response.status_code}, body={data}")

    return data


def extract_email_list(inbox_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    emails = inbox_data.get("data", {}).get("emails", [])
    if isinstance(emails, list):
        return emails
    return []


def find_target_email(emails: List[Dict[str, Any]], subject_keyword: str) -> Optional[Dict[str, Any]]:
    for item in emails:
        subject = str(item.get("subject", ""))
        if subject_keyword in subject:
            return item
    return None


def poll_for_email(
    client: ChatGPTMailClient,
    email: str,
    inbox_token: str,
    subject_keyword: str,
    timeout_seconds: int = POLL_TIMEOUT_SECONDS,
    interval_seconds: int = POLL_INTERVAL_SECONDS,
) -> Dict[str, Any]:
    deadline = time.time() + timeout_seconds
    last_inbox_data: Dict[str, Any] = {}

    while time.time() < deadline:
        inbox_data = client.list_emails(email, inbox_token)
        last_inbox_data = inbox_data

        emails = extract_email_list(inbox_data)
        target = find_target_email(emails, subject_keyword)
        if target:
            return target

        print(f"[轮询] 暂未找到目标邮件，当前邮件数: {len(emails)}，{interval_seconds} 秒后重试...")
        time.sleep(interval_seconds)

    raise TimeoutError(f"在 {timeout_seconds} 秒内未收到目标邮件。最后一次收件箱结果: {last_inbox_data}")


def main() -> None:
    print("=== ChatGPTMail + Resend 测试开始 ===")
    print(f"SMTP 配置记录: {SMTP_SERVER}:{SMTP_PORT}, username={SMTP_USERNAME}")
    print("本次发信默认使用 Resend HTTP API，而不是 SMTP。")

    client = ChatGPTMailClient()
    email, inbox_token, raw_generate_data = client.generate_email()
    print(f"[成功] 生成临时邮箱: {email}")
    print(f"[成功] Inbox Token: {inbox_token}")
    print(f"[调试] 生成邮箱原始返回: {json.dumps(raw_generate_data, ensure_ascii=False)}")

    subject_keyword = f"CHATGPTMAIL-TEST-{int(time.time())}"
    text_body = (
        "这是一封测试邮件，用于验证 ChatGPTMail 收件流程是否正常。\n"
        f"目标邮箱: {email}\n"
        f"主题关键字: {subject_keyword}\n"
    )
    html_body = f"""
    <html>
      <body>
        <h1>ChatGPTMail Test</h1>
        <p>这是一封测试邮件，用于验证 ChatGPTMail 收件流程是否正常。</p>
        <p><strong>目标邮箱:</strong> {email}</p>
        <p><strong>主题关键字:</strong> {subject_keyword}</p>
      </body>
    </html>
    """

    send_result = send_test_email_via_resend_api(
        api_key=RESEND_API_KEY,
        from_email=SENDER_EMAIL,
        to_email=email,
        subject=subject_keyword,
        html=html_body,
        text=text_body,
    )
    print(f"[成功] Resend 发信成功: {json.dumps(send_result, ensure_ascii=False)}")

    matched_email = poll_for_email(
        client=client,
        email=email,
        inbox_token=inbox_token,
        subject_keyword=subject_keyword,
    )
    print(f"[成功] 收到目标邮件: {json.dumps(matched_email, ensure_ascii=False)}")

    email_id = matched_email.get("id")
    if email_id:
        detail = client.get_email_detail(str(email_id), inbox_token)
        print(f"[成功] 邮件详情: {json.dumps(detail, ensure_ascii=False)}")
    else:
        print("[提示] 目标邮件中没有 id，跳过详情拉取。")

    print("=== 测试完成：发信与收信链路正常 ===")


if __name__ == "__main__":
    main()