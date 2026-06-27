"""Providers package — 10 个经过实测验证的临时邮箱 provider."""

from .inboxkitten import InboxkittenClient as InboxKittenClient
from .mailnesia import MailnesiaClient
from .anonymmail import AnonymmailClient
from .tempmail_lol import TempMailLolClient
from .chatgptmail import ChatGPTMailClient
from .tempmail_ing import TempMailIngClient
from .emailtick import EmailTickClient
from .guerrillamail import GuerrillaMailClient
from .maildrop import MaildropClient
from .mailtm import MailTmClient

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
    "EmailTickClient",
    "GuerrillaMailClient",
    "MaildropClient",
    "MailTmClient",
    "TempEmail", "InboxEmail", "ETagCache",
    "TempMailError", "EmailGenerateError", "EmailFetchError", "RateLimitError",
]
