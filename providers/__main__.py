"""
python -m providers  — 列出所有可用的 provider
"""

from providers import (
    BoomlifyClient,
    ChatGPTMailClient,
    EmailnatorClient,
    GuerrillaMailClient,
    MailTmClient,
    MohmalClient,
    TempMailIngClient,
    TempMailOrgClient,
    YopmailClient,
)

CLIENTS = [
    TempMailIngClient,
    BoomlifyClient,
    ChatGPTMailClient,
    GuerrillaMailClient,
    MailTmClient,
    EmailnatorClient,
    MohmalClient,
    TempMailOrgClient,
    YopmailClient,
]

def main():
    print("📧 可用的临时邮箱 Provider:\n")
    for cls in CLIENTS:
        client = cls()
        print(f"  • {client.provider_name:<20} ({cls.__name__})")
    print(f"\n共 {len(CLIENTS)} 个 provider")
    print("\n使用方式:")
    print("  from providers import TempMailIngClient")
    print("  client = TempMailIngClient()")
    print("  email = client.generate_email()")

if __name__ == "__main__":
    main()
