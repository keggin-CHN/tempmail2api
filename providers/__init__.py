"""
临时邮箱客户端统一接口
支持 chatgptmail / tempmail.ing / boomlify 三个平台
"""

from .base import TempMailClient
from .chatgptmail import ChatGPTMailClient
from .tempmail_ing import TempMailIngClient
from .boomlify import BoomlifyClient

__all__ = [
    "TempMailClient",
    "ChatGPTMailClient",
    "TempMailIngClient",
    "BoomlifyClient",
]
