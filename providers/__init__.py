"""Providers package — 4 个经过实测验证的临时邮箱 provider."""

from .inboxkitten import InboxkittenClient as InboxKittenClient
from .mailnesia import MailnesiaClient
from .anonymmail import AnonymmailClient
from .tempmail_lol import TempMailLolClient
from .chatgptmail import ChatGPTMailClient
from .tempmail_ing import TempMailIngClient

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
    "TempEmail", "InboxEmail", "ETagCache",
    "TempMailError", "EmailGenerateError", "EmailFetchError", "RateLimitError",
]
