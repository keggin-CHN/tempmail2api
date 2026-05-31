"""GuerrillaMail aliases — grr.la, guerrillamail.info, etc."""

from .guerrillamail import GuerrillaMailClient


class GrrLaClient(GuerrillaMailClient):
    """Client for https://grr.la/ — GuerrillaMail alias."""
    @property
    def provider_name(self) -> str:
        return "grr.la"


class GuerrillamailInfoClient(GuerrillaMailClient):
    """Client for https://guerrillamail.info/ — GuerrillaMail alias."""
    @property
    def provider_name(self) -> str:
        return "guerrillamail.info"


class GuerrillamailBizClient(GuerrillaMailClient):
    """Client for https://guerrillamail.biz/ — GuerrillaMail alias."""
    @property
    def provider_name(self) -> str:
        return "guerrillamail.biz"


class GuerrillamailNetClient(GuerrillaMailClient):
    """Client for https://guerrillamail.net/ — GuerrillaMail alias."""
    @property
    def provider_name(self) -> str:
        return "guerrillamail.net"


class GuerrillamailOrgClient(GuerrillaMailClient):
    """Client for https://guerrillamail.org/ — GuerrillaMail alias."""
    @property
    def provider_name(self) -> str:
        return "guerrillamail.org"


class GuerrillamailblockClient(GuerrillaMailClient):
    """Client for https://guerrillamailblock.com/ — GuerrillaMail alias."""
    @property
    def provider_name(self) -> str:
        return "guerrillamailblock"
