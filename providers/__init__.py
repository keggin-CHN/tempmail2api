"""
临时邮箱客户端统一接口
支持 chatgptmail / tempmail.ing / boomlify / guerrillamail 四个平台
"""

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
from .utils import ETagCache, TempMailError, EmailGenerateError, EmailFetchError, RateLimitError

__all__ = [
    # 客户端
    "TempMailClient",
    "ChatGPTMailClient",
    "TempMailIngClient",
    "BoomlifyClient",
    "GuerrillaMailClient",
    "MailTmClient",
    "EmailnatorClient",
    "MohmalClient",
    "TempMailLolClient",
    "TempMailOrgClient",
    "YopmailClient",
    # 数据模型
    "TempEmail",
    "InboxEmail",
    # 工具
    "ETagCache",
    # 异常
    "TempMailError",
    "EmailGenerateError",
    "EmailFetchError",
    "RateLimitError",
]
