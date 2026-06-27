"""Providers package — 11 个经过实测验证的临时邮箱 provider."""

from .inboxkitten import InboxkittenClient as InboxKittenClient
from .mailnesia import MailnesiaClient
from .anonymmail import AnonymmailClient
from .tempmail_lol import TempMailLolClient
from .chatgptmail import ChatGPTMailClient
from .tempmail_ing import TempMailIngClient
from .guerrillamail import GuerrillaMailClient
from .maildrop import MaildropClient
from .mailtm import MailTmClient
from .minmail import MinMailClient
from .tempmail_plus import TempMailPlusClient

# Re-export base types
from .base import TempMailClient, TempEmail, InboxEmail
from .utils import ETagCache, TempMailError, EmailGenerateError, EmailFetchError, RateLimitError

__all__ = [
    "TempMailClient",
    "InboxKittenClient",
    "MailnesiaClient",
    "AnonymmailClient",
    "TempMailLolClient",
    "ChatGPTMailClient",
    "TempMailIngClient",
    "GuerrillaMailClient",
    "MaildropClient",
    "MailTmClient",
    "MinMailClient",
    "TempMailPlusClient",
    "TempEmail", "InboxEmail", "ETagCache",
    "TempMailError", "EmailGenerateError", "EmailFetchError", "RateLimitError",
]
