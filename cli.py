#!/usr/bin/env python3
"""
命令行工具 — 4 个经实测验证的临时邮箱 provider

用法:
    python cli.py generate --provider inboxkitten
    python cli.py inbox --address xxx@inboxkitten.com --provider inboxkitten
    python cli.py providers
"""

import argparse
import json
import sys

from providers.inboxkitten import InboxkittenClient as InboxKittenClient
from providers.mailnesia import MailnesiaClient
from providers.anonymmail import AnonymmailClient
from providers.tempmail_lol import TempMailLolClient
from providers.chatgptmail import ChatGPTMailClient
from providers.tempmail_ing import TempMailIngClient

from typing import Optional

PROVIDERS = {
    "inboxkitten": InboxKittenClient,
    "mailnesia": MailnesiaClient,
    "anonymmail": AnonymmailClient,
    "tempmaillol": TempMailLolClient,
    "tempmail.lol": TempMailLolClient,
    "chatgptmail": ChatGPTMailClient,
    "tempmail": TempMailIngClient,
    "tempmailing": TempMailIngClient,
}


def detect_provider(address: str) -> Optional[str]:
    """根据邮箱地址猜测 provider"""
    domain = address.split("@")[-1].lower() if "@" in address else ""
    
    domain_map = {
        "inboxkitten.com": "inboxkitten",
        "mailnesia.com": "mailnesia",
        "anonymmail.net": "anonymmail",
    }
    
    for d, p in domain_map.items():
        if d in domain:
            return p
    
    return None


def cmd_generate(args):
    provider = args.provider
    if not provider:
        provider = "inboxkitten"
    
    client_cls = PROVIDERS.get(provider)
    if not client_cls:
        print(f"❌ 未知 provider: {provider}")
        print(f"   可用: {', '.join(PROVIDERS.keys())}")
        sys.exit(1)
    
    try:
        client = client_cls()
        email = client.generate_email()
        
        if args.json:
            print(json.dumps({
                "address": email.address,
                "provider": email.provider,
                "created_at": email.created_at,
            }, ensure_ascii=False, indent=2))
        else:
            print(f"📧 临时邮箱已生成")
            print(f"   地址: {email.address}")
            print(f"   Provider: {email.provider}")
            print(f"   创建时间: {email.created_at}")
    except Exception as e:
        print(f"❌ 生成失败: {e}")
        sys.exit(1)


def cmd_inbox(args):
    address = args.address
    if not address:
        print("❌ 请指定 --address")
        sys.exit(1)
    
    provider = args.provider
    if not provider:
        provider = detect_provider(address)
        if not provider:
            print(f"❌ 无法从地址推断 provider，请用 --provider 指定")
            sys.exit(1)
        print(f"🔍 自动检测 provider: {provider}")
    
    client_cls = PROVIDERS.get(provider)
    if not client_cls:
        print(f"❌ 未知 provider: {provider}")
        sys.exit(1)
    
    try:
        client = client_cls()
        
        if args.id:
            detail = client.get_email_detail(address, args.id)
            if args.json:
                print(json.dumps({
                    "id": detail.id,
                    "subject": detail.subject,
                    "from_address": detail.from_address,
                    "body_html": detail.body_html,
                    "body_text": detail.body_text,
                    "date": detail.date,
                }, ensure_ascii=False, indent=2))
            else:
                print(f"📧 邮件详情")
                print(f"   ID: {detail.id}")
                print(f"   主题: {detail.subject}")
                print(f"   发件人: {detail.from_address}")
                print(f"   时间: {detail.date}")
                print(f"   正文:\n{detail.body_text or detail.body_html}")
        else:
            emails = client.list_emails(address)
            if args.json:
                print(json.dumps({
                    "address": address,
                    "count": len(emails),
                    "emails": [vars(e) for e in emails],
                }, ensure_ascii=False, indent=2))
            else:
                print(f"📬 收件箱 ({address})")
                print(f"   {len(emails)} 封邮件")
                for e in emails:
                    print(f"   [{e.id}] {e.from_address} — {e.subject}")
    except Exception as e:
        print(f"❌ 查询失败: {e}")
        sys.exit(1)


def cmd_providers(args):
    if args.json:
        print(json.dumps({
            "providers": list(PROVIDERS.keys()),
            "verified": ["inboxkitten", "mailnesia", "anonymmail", "tempmaillol"],
        }, ensure_ascii=False, indent=2))
    else:
        print("📋 可用 Provider:")
        for name in PROVIDERS.keys():
            print(f"  • {name}")


def main():
    parser = argparse.ArgumentParser(description="临时邮箱 CLI — 4 个经实测验证的 provider")
    parser.add_argument("--json", action="store_true", help="JSON 格式输出")
    sub = parser.add_subparsers(dest="command")
    
    # generate
    gen = sub.add_parser("generate", help="生成临时邮箱")
    gen.add_argument("--provider", "-p", help="Provider 名称")
    
    # inbox
    inbox = sub.add_parser("inbox", help="查看收件箱")
    inbox.add_argument("--address", "-a", help="邮箱地址")
    inbox.add_argument("--provider", "-p", help="Provider 名称")
    inbox.add_argument("--id", help="查看指定邮件 ID 的详情")
    
    # providers
    sub.add_parser("providers", help="列出可用 provider")
    
    args = parser.parse_args()
    
    if args.command == "generate":
        cmd_generate(args)
    elif args.command == "inbox":
        cmd_inbox(args)
    elif args.command == "providers":
        cmd_providers(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
