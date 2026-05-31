"""Internxt.com temporary email — alias for Mail.tm API."""

from .mail_tm import MailTmClient


class InternxtClient(MailTmClient):
    """Client for https://internxt.com/temporary-email — uses Mail.tm API."""

    @property
    def provider_name(self) -> str:
        return "internxt"
