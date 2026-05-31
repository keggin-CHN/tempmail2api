#!/usr/bin/env python3
"""
测试 chatgptmail-2api 的 provider 能否真正收到邮件
通过 WayinVideo 注册发验证码来验证
"""

import sys
import os
import time
import re
import json
import hashlib
import base64

sys.path.insert(0, "/tmp/chatgptmail-2api")

from curl_cffi import requests as curl_requests

# WayinVideo API
WAYIN_API = "https://wayinvideo-api.wayin.ai"

# 要测试的 provider 列表 (名称, 模块, 类)
PROVIDERS_TO_TEST = [
    ("1secmail", "providers.onesecmail", "OnesecmailClient"),
    ("mail.tm", "providers.mail_tm", "MailTmClient"),
    ("guerrillamail", "providers.guerrillamail", "GuerrillaMailClient"),
    ("tempmail.lol", "providers.tempmail_lol", "TempMailLolClient"),
    ("adguard", "providers.adguard", "AdguardClient"),
    ("noopmail", "providers.noopmail", "NoopmailClient"),
    ("tempomail", "providers.tempomail", "TempomailClient"),
    ("inboxkitten", "providers.inboxkitten", "InboxkittenClient"),
    ("anonymmail", "providers.anonymmail", "AnonymmailClient"),
    ("mailnesia", "providers.mailnesia", "MailnesiaClient"),
]

POLL_TIMEOUT = 60
POLL_INTERVAL = 5


def compute_ticket(reason, email, timestamp_ms):
    raw = f"{reason}{email}{timestamp_ms}"
    md5_hex = hashlib.md5(raw.encode()).hexdigest()
    return base64.b64encode(md5_hex.encode()).decode()


def send_verify_code(email):
    """Send WayinVideo verify code to email"""
    reason = "SIGNUP"
    ts = int(time.time() * 1000)
    ticket = compute_ticket(reason, email, ts)
    session = curl_requests.Session(impersonate="chrome136")
    body = json.dumps({
        "email": email,
        "reason": reason,
        "timestamp": ts,
        "ticket": ticket,
    })
    r = session.post(
        f"{WAYIN_API}/verify_code",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    r.raise_for_status()
    return "code" in r.text.lower() and ("0" in r.text or "success" in r.text.lower())


def find_code_in_emails(emails_detail):
    """Look for 6-digit verification code in email content"""
    text = json.dumps(emails_detail, ensure_ascii=False)
    for pattern in [r'verification code[:\s]*(\d{6})', r'code[:\s]*(\d{6})',
                    r'验证码[：:\s]*(\d{6})', r'\b(\d{6})\b']:
        m = re.search(pattern, text, re.I)
        if m:
            return m.group(1)
    return None


def test_provider(name, module_name, class_name):
    """Test a single provider: generate email, send verify code, poll for result"""
    print(f"\n{'='*50}")
    print(f"🧪 测试 Provider: {name}")
    print(f"{'='*50}")

    try:
        # Import provider
        mod = __import__(module_name, fromlist=[class_name])
        cls = getattr(mod, class_name)
        client = cls()

        # 1. Generate email
        print(f"  📧 生成邮箱...")
        email_obj = client.generate_email()
        address = email_obj.address
        print(f"  ✅ 邮箱: {address}")

        # 2. Send verify code
        print(f"  📤 发送 WayinVideo 验证码...")
        try:
            send_result = send_verify_code(address)
            print(f"  {'✅' if send_result else '⚠️'} 发送结果: {send_result}")
        except Exception as e:
            print(f"  ❌ 发送失败: {e}")
            return {"provider": name, "email": address, "status": "send_failed", "error": str(e)}

        # 3. Poll for code
        print(f"  ⏳ 等待验证码 (最多 {POLL_TIMEOUT}s)...")
        deadline = time.time() + POLL_TIMEOUT
        found = False
        while time.time() < deadline:
            try:
                emails = client.list_emails(address)
                if emails:
                    print(f"  📬 收到 {len(emails)} 封邮件")
                    for e in emails:
                        subj = e.subject if hasattr(e, 'subject') else str(e)
                        print(f"     - {subj}")
                    # Try to get detail and find code
                    for e in emails:
                        try:
                            eid = e.id if hasattr(e, 'id') else str(e)
                            detail = client.get_email_detail(address, eid)
                            if detail:
                                body = ""
                                if hasattr(detail, 'body_html') and detail.body_html:
                                    body = detail.body_html
                                elif hasattr(detail, 'body_text') and detail.body_text:
                                    body = detail.body_text
                                code_match = re.search(r'\b(\d{6})\b', body)
                                if code_match:
                                    print(f"  ✅ 找到验证码: {code_match.group(1)}")
                                    found = True
                                    break
                        except Exception:
                            continue
                    if found:
                        break
            except Exception as e:
                pass  # Some providers may fail on first poll
            time.sleep(POLL_INTERVAL)

        if found:
            result = {"provider": name, "email": address, "status": "✅ 成功收到验证码"}
        else:
            result = {"provider": name, "email": address, "status": "⚠️ 超时未收到验证码"}
        print(f"  结果: {result['status']}")
        return result

    except Exception as e:
        print(f"  ❌ Provider 初始化失败: {e}")
        return {"provider": name, "status": "❌ 初始化失败", "error": str(e)}


def main():
    print("╔══════════════════════════════════════════════════╗")
    print("║   ChatGPTMail-2API Provider 实际收信测试        ║")
    print("║   通过 WayinVideo 验证码测试                    ║")
    print("╚══════════════════════════════════════════════════╝")

    results = []
    for name, module_name, class_name in PROVIDERS_TO_TEST:
        result = test_provider(name, module_name, class_name)
        results.append(result)
        time.sleep(2)

    # Summary
    print(f"\n{'='*50}")
    print("📊 测试结果汇总:")
    print(f"{'='*50}")
    for r in results:
        print(f"  {r['provider']:<20} {r['status']}")
        if r.get('email'):
            print(f"    邮箱: {r['email']}")

    # Save results
    with open("/tmp/provider_test_results.json", "w") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n结果已保存到 /tmp/provider_test_results.json")


if __name__ == "__main__":
    main()
