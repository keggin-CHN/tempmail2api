"""临时邮箱客户端统一接口 — 39 个 provider"""
from .base import TempMailClient, TempEmail, InboxEmail
from .chatgptmail import ChatGPTMailClient
from .tempmail_ing import TempMailIngClient
from .boomlify import BoomlifyClient
from .guerrillamail import GuerrillaMailClient
from .mail_tm import MailTmClient
from .emailnator import EmailnatorClient
from .mohmal import MohmalClient
from .tempmail_lol import TempMailLolClient
from .tempmail_org import TempMailOrgClient
from .yopmail import YopmailClient
from .mail_gw import MailGwClient
from .harakirimail import HarakirimailClient
from .tempmail_plus import TempMailPlusClient
from .inboxes import InboxesClient
from .noopmail import NoopmailClient
from .mailnesia import MailnesiaClient
from .moakt import MoaktClient
from .fakemail_net import FakemailNetClient
from .emailfake import EmailfakeClient
from .tempomail import TempomailClient
from .anonymmail import AnonymmailClient
from .emailondeck import EmailondeckClient
from .etempmail import EtempmailClient
from .tempm import TempmClient
from .generator_email import GeneratorEmailClient
from .emaildashfake import EmaildashfakeClient
from .adguard import AdguardClient
from .inboxkitten import InboxkittenClient
from .disposablemail import DisposablemailClient
from .fakemailgenerator import FakemailgeneratorClient
from .trashmail import TrashmailClient
from .onesecmail import OnesecmailClient
from .maildax import MaildaxClient
from .fakermail import FakermailClient
from .mintemail import MintemailClient
from .eztempmail import EztempmailClient
from .tmail_gg import TmailGgClient
from .tempemail_co import TempemailCoClient
from .mailgolem import MailgolemClient
from .utils import ETagCache, TempMailError, EmailGenerateError, EmailFetchError, RateLimitError

__all__ = [
    "TempMailClient", "ChatGPTMailClient", "TempMailIngClient", "BoomlifyClient",
    "GuerrillaMailClient", "MailTmClient", "EmailnatorClient", "MohmalClient",
    "TempMailLolClient", "TempMailOrgClient", "YopmailClient", "MailGwClient",
    "HarakirimailClient", "TempMailPlusClient", "InboxesClient", "NoopmailClient",
    "MailnesiaClient", "MoaktClient", "FakemailNetClient", "EmailfakeClient",
    "TempomailClient", "AnonymmailClient", "EmailondeckClient", "EtempmailClient",
    "TempmClient", "GeneratorEmailClient", "EmaildashfakeClient", "AdguardClient",
    "InboxkittenClient", "DisposablemailClient", "FakemailgeneratorClient",
    "TrashmailClient", "OnesecmailClient", "MaildaxClient", "FakermailClient",
    "MintemailClient", "EztempmailClient", "TmailGgClient", "TempemailCoClient",
    "MailgolemClient",
    "TempEmail", "InboxEmail", "ETagCache",
    "TempMailError", "EmailGenerateError", "EmailFetchError", "RateLimitError",
]
