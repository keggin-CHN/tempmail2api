"""Tempmail.email provider — alias for Mail.tm API."""

from .mail_tm import MailTmClient


class TempmailEmailClient(MailTmClient):
    """Client for https://tempmail.email/ — uses Mail.tm API."""

    @property
    def provider_name(self) -> str:
        return "tempmail.email"
