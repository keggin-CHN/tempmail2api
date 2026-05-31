"""Mail-temp.com provider — alias for Generator.email pattern."""

import random
import string
from typing import Optional

from .generator_email import GeneratorEmailClient


class MailTempClient(GeneratorEmailClient):
    """Client for https://mail-temp.com/ — uses Generatoremail pattern."""

    BASE_URL = "https://mail-temp.com"

    def __init__(self, proxy: Optional[str] = None, timeout: int = 30):
        super().__init__(proxy=proxy, timeout=timeout)

    @property
    def provider_name(self) -> str:
        return "mail-temp"
