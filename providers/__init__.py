"""临时邮箱客户端统一接口 — 17 个 provider"""
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
from .utils import ETagCache, TempMailError, EmailGenerateError, EmailFetchError, RateLimitError

__all__ = [
    "TempMailClient", "ChatGPTMailClient", "TempMailIngClient", "BoomlifyClient",
    "GuerrillaMailClient", "MailTmClient", "EmailnatorClient", "MohmalClient",
    "TempMailLolClient", "TempMailOrgClient", "YopmailClient", "MailGwClient",
    "HarakirimailClient", "TempMailPlusClient", "InboxesClient", "NoopmailClient",
    "MailnesiaClient", "MoaktClient",
    "TempEmail", "InboxEmail", "ETagCache",
    "TempMailError", "EmailGenerateError", "EmailFetchError", "RateLimitError",
]
