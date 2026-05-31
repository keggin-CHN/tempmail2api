#!/usr/bin/env python3
"""
多平台临时邮箱端到端测试脚本
支持 chatgptmail / tempmail.ing / boomlify / guerrillamail 四个平台

环境要求：Python 3.8+
pip install curl_cffi requests

用法：
    python examples/demo_all.py              # 测试所有平台
    python examples/demo_all.py tempmail     # 仅测试 tempmail.ing
    python examples/demo_all.py boomlify     # 仅测试 boomlify
    python examples/demo_all.py chatgptmail  # 仅测试 chatgptmail
    python examples/demo_all.py guerrillamail # 仅测试 guerrillamail
"""

import json
import sys
import time
from typing import List

# 添加项目根目录到 path
sys.path.insert(0, ".")

from providers.base import InboxEmail, TempEmail, TempMailClient
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

POLL_INTERVAL = 5
POLL_TIMEOUT = 120


def test_provider(client: TempMailClient) -> None:
    """测试单个 provider 的完整流程"""
    name = client.provider_name
    print(f"\n{'='*60}")
    print(f"  测试 {name}")
    print(f"{'='*60}")

    # 1. 生成邮箱
    print(f"\n[1] 生成临时邮箱...")
    try:
        email = client.generate_email(duration_minutes=10)
        print(f"  ✅ 邮箱: {email.address}")
        print(f"  ⏰ 过期: {email.expires_at}")
    except Exception as e:
        print(f"  ❌ 生成失败: {e}")
        return

    # 2. 检查收件箱（应该为空）
    print(f"\n[2] 检查收件箱...")
    try:
        emails = client.list_emails(email.address)
        print(f"  ✅ 当前邮件数: {len(emails)}")
    except Exception as e:
        print(f"  ❌ 查看收件箱失败: {e}")
        return

    # 3. 输出原始数据
    print(f"\n[3] 原始生成响应:")
    print(f"  {json.dumps(email.raw, ensure_ascii=False, indent=2)[:500]}")

    print(f"\n✅ {name} 测试通过！")
    print(f"   邮箱地址: {email.address}")
    print(f"   提示: 发送邮件到 {email.address} 后运行 list_emails() 查看")


def main() -> None:
    providers = {
        "tempmail": TempMailIngClient,
        "boomlify": BoomlifyClient,
        "chatgptmail": ChatGPTMailClient,
        "guerrillamail": GuerrillaMailClient,
        "mailtm": MailTmClient,
        "emailnator": EmailnatorClient,
        "mohmal": MohmalClient,
        "tempmailorg": TempMailOrgClient,
        "tempmaillol": TempMailLolClient,
        "yopmail": YopmailClient,
        "mailgw": MailGwClient,
        "harakirimail": HarakirimailClient,
        "tempmailplus": TempMailPlusClient,
        "inboxes": InboxesClient,
        "noopmail": NoopmailClient,
        "mailnesia": MailnesiaClient,
        "moakt": MoaktClient,
        "fakemailnet": FakemailNetClient,
        "emailfake": EmailfakeClient,
    }

    # 命令行参数选择 provider
    if len(sys.argv) > 1:
        selected = sys.argv[1].lower()
        if selected not in providers:
            print(f"未知 provider: {selected}")
            print(f"可选: {', '.join(providers.keys())}")
            sys.exit(1)
        targets = {selected: providers[selected]}
    else:
        targets = providers

    print("🚀 多平台临时邮箱测试")
    print(f"   Python 版本测试时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")

    for name, client_cls in targets.items():
        try:
            client = client_cls()
            test_provider(client)
        except Exception as e:
            print(f"\n❌ {name} 测试失败: {e}")

    print(f"\n{'='*60}")
    print("  测试完成")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
