"""python -m providers — list all providers"""
from providers import (
    BoomlifyClient, ChatGPTMailClient, EmailnatorClient, EmailfakeClient,
    FakemailNetClient, GuerrillaMailClient, HarakirimailClient, InboxesClient,
    MailGwClient, MailTmClient, MohmalClient, MoaktClient, MailnesiaClient,
    NoopmailClient, TempMailIngClient, TempMailLolClient, TempMailOrgClient,
    TempMailPlusClient, YopmailClient,
)

CLIENTS = [
    TempMailIngClient, BoomlifyClient, ChatGPTMailClient, GuerrillaMailClient,
    MailTmClient, EmailnatorClient, MohmalClient, TempMailOrgClient,
    TempMailLolClient, YopmailClient, MailGwClient, HarakirimailClient,
    TempMailPlusClient, InboxesClient, NoopmailClient, MailnesiaClient,
    MoaktClient, FakemailNetClient, EmailfakeClient,
]

def main():
    print("📧 可用的临时邮箱 Provider:\n")
    for cls in CLIENTS:
        client = cls()
        print(f"  • {client.provider_name:<20} ({cls.__name__})")
    print(f"\n共 {len(CLIENTS)} 个 provider")

if __name__ == "__main__":
    main()
