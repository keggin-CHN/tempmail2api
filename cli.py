#!/usr/bin/env python3
"""
多平台临时邮箱 CLI 工具

用法:
    python -m cli generate tempmail            # 用 tempmail.ing 生成邮箱
    python -m cli generate boomlify            # 用 boomlify 生成邮箱
    python -m cli generate chatgptmail         # 用 chatgptmail 生成邮箱
    python -m cli generate guerrillamail       # 用 guerrillamail 生成邮箱
    python -m cli inbox <email_address>        # 查看收件箱（自动识别 provider）
    python -m cli wait <email_address>         # 等待新邮件到达
    python -m cli domains boomlify             # 查看 boomlify 可用域名
"""

import argparse
import sys
import time
from typing import Optional

from providers.base import TempMailClient
from providers.boomlify import BoomlifyClient
from providers.chatgptmail import ChatGPTMailClient
from providers.emailnator import EmailnatorClient
from providers.guerrillamail import GuerrillaMailClient
from providers.mail_tm import MailTmClient
from providers.mohmal import MohmalClient
from providers.tempmail_ing import TempMailIngClient
from providers.tempmail_lol import TempMailLolClient
from providers.tempmail_org import TempMailOrgClient
from providers.yopmail import YopmailClient
from providers.mail_gw import MailGwClient
from providers.harakirimail import HarakirimailClient
from providers.tempmail_plus import TempMailPlusClient
from providers.inboxes import InboxesClient
from providers.noopmail import NoopmailClient
from providers.mailnesia import MailnesiaClient
from providers.moakt import MoaktClient
from providers.fakemail_net import FakemailNetClient
from providers.emailfake import EmailfakeClient
from providers.tempomail import TempomailClient
from providers.anonymmail import AnonymmailClient
from providers.emailondeck import EmailondeckClient
from providers.etempmail import EtempmailClient
from providers.tempm import TempmClient
from providers.generator_email import GeneratorEmailClient
from providers.emaildashfake import EmaildashfakeClient
from providers.adguard import AdguardClient
from providers.inboxkitten import InboxkittenClient
from providers.disposablemail import DisposablemailClient
from providers.fakemailgenerator import FakemailgeneratorClient
from providers.trashmail import TrashmailClient
from providers.onesecmail import OnesecmailClient
from providers.maildax import MaildaxClient
from providers.fakermail import FakermailClient
from providers.mintemail import MintemailClient
from providers.eztempmail import EztempmailClient
from providers.tmail_gg import TmailGgClient
from providers.tempemail_co import TempemailCoClient
from providers.mailgolem import MailgolemClient
from providers.muellmail import MuellmailClient
from providers.mailsac import MailsacClient
from providers.tempmail_guru import TempmailGuruClient
from providers.crazymailing import CrazymailingClient
from providers.eyepaste import EyepasteClient
from providers.segamail import SegamailClient
from providers.tempmails_net import TempmailsNetClient
from providers.tempmailso import TempmailsoClient
from providers.haribu import HaribuClient
from providers.incognitomail import IncognitomailClient
from providers.tempmail_email import TempmailEmailClient
from providers.internxt import InternxtClient
from providers.lroid import LroidClient


PROVIDERS = {
    "tempmail": TempMailIngClient,
    "tempmailing": TempMailIngClient,
    "boomlify": BoomlifyClient,
    "chatgptmail": ChatGPTMailClient,
    "guerrillamail": GuerrillaMailClient,
    "guerrilla": GuerrillaMailClient,
    "mailtm": MailTmClient,
    "mail.tm": MailTmClient,
    "emailnator": EmailnatorClient,
    "mohmal": MohmalClient,
    "tempmailorg": TempMailOrgClient,
    "temp-mail.org": TempMailOrgClient,
    "tempmaillol": TempMailLolClient,
    "tempmail.lol": TempMailLolClient,
    "yopmail": YopmailClient,
    "mailgw": MailGwClient,
    "mail.gw": MailGwClient,
    "harakirimail": HarakirimailClient,
    "harakiri": HarakirimailClient,
    "tempmailplus": TempMailPlusClient,
    "tempmail.plus": TempMailPlusClient,
    "inboxes": InboxesClient,
    "inboxes.com": InboxesClient,
    "noopmail": NoopmailClient,
    "mailnesia": MailnesiaClient,
    "moakt": MoaktClient,
    "fakemailnet": FakemailNetClient,
    "fakemail.net": FakemailNetClient,
    "emailfake": EmailfakeClient,
    "tempomail": TempomailClient,
    "anonymmail": AnonymmailClient,
    "emailondeck": EmailondeckClient,
    "etempmail": EtempmailClient,
    "tempm": TempmClient,
    "generator.email": GeneratorEmailClient,
    "email-fake": EmaildashfakeClient,
    "emaildashfake": EmaildashfakeClient,
    "adguard": AdguardClient,
    "inboxkitten": InboxkittenClient,
    "disposablemail": DisposablemailClient,
    "fakemailgenerator": FakemailgeneratorClient,
    "trashmail": TrashmailClient,
    "1secmail": OnesecmailClient,
    "onesecmail": OnesecmailClient,
    "maildax": MaildaxClient,
    "fakermail": FakermailClient,
    "mintemail": MintemailClient,
    "eztempmail": EztempmailClient,
    "tmail.gg": TmailGgClient,
    "tempemail.co": TempemailCoClient,
    "mailgolem": MailgolemClient,
    "muellmail": MuellmailClient,
    "mailsac": MailsacClient,
    "tempmail.guru": TempmailGuruClient,
    "crazymailing": CrazymailingClient,
    "eyepaste": EyepasteClient,
    "segamail": SegamailClient,
    "tempmails.net": TempmailsNetClient,
    "tempmailso": TempmailsoClient,
    "haribu": HaribuClient,
    "incognitomail": IncognitomailClient,
    "tempmail.email": TempmailEmailClient,
    "internxt": InternxtClient,
    "lroid": LroidClient,
}


def detect_provider(address: str) -> Optional[str]:
    """根据邮箱地址猜测 provider"""
    domain = address.split("@")[-1].lower()
    if "openclawskill" in domain or "chatgpt" in domain:
        return "chatgptmail"
    if "okcx.edu" in domain or "priyo.edu" in domain or "boomlify" in domain:
        return "boomlify"
    if "guerrillamail" in domain or "guerrillamailblock" in domain or "grr.la" in domain:
        return "guerrillamail"
    if domain == "mail.tm":
        return "mailtm"
    if domain == "mail.gw":
        return "mailgw"
    if domain == "gmail.com":
        return "emailnator"
    if "emailinbo" in domain or "mohmal" in domain:
        return "mohmal"
    if "yopmail" in domain:
        return "yopmail"
    if "harakirimail" in domain:
        return "harakirimail"
    if "mailto.plus" in domain or "tempmail.plus" in domain:
        return "tempmailplus"
    if "inboxes" in domain:
        return "inboxes"
    # tempmail.ing / temp-mail.org / tempmail.lol 使用各种随机域名
    return None


def get_client(provider_name: Optional[str] = None, address: Optional[str] = None) -> TempMailClient:
    """获取客户端实例"""
    if provider_name and provider_name in PROVIDERS:
        return PROVIDERS[provider_name]()

    if address:
        detected = detect_provider(address)
        if detected and detected in PROVIDERS:
            return PROVIDERS[detected]()

    # 默认用 tempmail.ing
    return TempMailIngClient()


def cmd_generate(args):
    """生成临时邮箱"""
    client = get_client(args.provider)
    email = client.generate_email(duration_minutes=args.duration, domain=args.domain)
    if getattr(args, 'json', False):
        import json
        print(json.dumps(email.to_dict(), ensure_ascii=False))
        return
    print(f"📧 邮箱地址: {email.address}")
    print(f"🏷️  Provider: {email.provider}")
    if email.expires_at:
        print(f"⏰ 过期时间: {email.expires_at}")
    print(f"\n💡 查看收件箱: python -m cli inbox {email.address}")

    if args.wait:
        print(f"\n⏳ 等待邮件中... (超时 {args.timeout}s)")
        received = client.wait_for_email(email.address, timeout=args.timeout)
        if received:
            print(f"\n📬 收到邮件!")
            print(f"   主题: {received.subject}")
            print(f"   发件人: {received.from_email}")
        else:
            print(f"\n⏰ 超时，未收到邮件")


def cmd_inbox(args):
    """查看收件箱"""
    client = get_client(args.provider, args.address)
    emails = client.list_emails(args.address)
    if getattr(args, 'json', False):
        import json
        result = [e.to_dict() for e in emails]
        print(json.dumps(result, ensure_ascii=False))
        return
    print(f"📬 {args.address} 的收件箱 ({len(emails)} 封邮件)")
    print(f"   Provider: {client.provider_name}")
    print()
    if not emails:
        print("   (空)")
        return
    for i, e in enumerate(emails, 1):
        print(f"  [{i}] {e.subject or '(无主题)'}")
        print(f"      发件人: {e.from_email or '未知'}")
        print(f"      时间: {e.received_at or '未知'}")
        print(f"      ID: {e.id}")
        if args.detail and e.id:
            try:
                detail = client.get_email_detail(e.id)
                if detail.body_text:
                    print(f"      正文: {detail.body_text[:200]}")
            except Exception:
                pass
        print()


def cmd_wait(args):
    """等待新邮件"""
    client = get_client(args.provider, args.address)
    print(f"⏳ 等待 {args.address} 的新邮件... (超时 {args.timeout}s)")
    received = client.wait_for_email(args.address, timeout=args.timeout, poll_interval=args.interval)
    if received:
        print(f"\n📬 收到邮件!")
        print(f"   主题: {received.subject}")
        print(f"   发件人: {received.from_email}")
        print(f"   ID: {received.id}")
    else:
        print(f"\n⏰ 超时 {args.timeout}s，未收到邮件")
        sys.exit(1)


def cmd_domains(args):
    """查看可用域名"""
    if args.provider != "boomlify":
        print("目前只有 boomlify 支持域名列表查询")
        return
    client = BoomlifyClient()
    domains = client.get_public_domains()
    print(f"🌐 Boomlify 可用域名 ({len(domains)} 个):")
    for d in domains:
        status = "✅" if d.get("is_active") else "❌"
        edu = " 🎓" if d.get("is_edu") else ""
        premium = " 💎" if d.get("is_premium") else ""
        print(f"  {status} {d['domain']}{edu}{premium}")


def main():
    parser = argparse.ArgumentParser(description="多平台临时邮箱 CLI")
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # generate
    gen = subparsers.add_parser("generate", help="生成临时邮箱")
    gen.add_argument("provider", nargs="?", default="tempmail", help="Provider 名称")
    gen.add_argument("-d", "--duration", type=int, default=10, help="有效期（分钟）")
    gen.add_argument("--domain", help="指定域名")
    gen.add_argument("-w", "--wait", action="store_true", help="生成后等待邮件")
    gen.add_argument("-t", "--timeout", type=int, default=120, help="等待超时秒数")

    # inbox
    inbox = subparsers.add_parser("inbox", help="查看收件箱")
    inbox.add_argument("address", help="邮箱地址")
    inbox.add_argument("-p", "--provider", help="Provider 名称")
    inbox.add_argument("--detail", action="store_true", help="显示邮件正文")

    # wait
    wait = subparsers.add_parser("wait", help="等待新邮件")
    wait.add_argument("address", help="邮箱地址")
    wait.add_argument("-p", "--provider", help="Provider 名称")
    wait.add_argument("-t", "--timeout", type=int, default=120, help="超时秒数")
    wait.add_argument("-i", "--interval", type=int, default=5, help="轮询间隔秒数")

    # domains
    dom = subparsers.add_parser("domains", help="查看可用域名")
    dom.add_argument("provider", nargs="?", default="boomlify", help="Provider 名称")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        return

    commands = {
        "generate": cmd_generate,
        "inbox": cmd_inbox,
        "wait": cmd_wait,
        "domains": cmd_domains,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
