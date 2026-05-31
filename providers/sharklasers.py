"""SharkLasers.com — alias for GuerrillaMail (sharklasers.com = guerrillamail.com)."""

from .guerrillamail import GuerrillaMailClient


class SharklasersClient(GuerrillaMailClient):
    """Client for https://sharklasers.com/ — uses GuerrillaMail API."""

    @property
    def provider_name(self) -> str:
        return "sharklasers"
