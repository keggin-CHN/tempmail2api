"""
Mock 单元测试 — 4 个经实测验证的 provider
"""

import unittest
from unittest.mock import MagicMock, patch, PropertyMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestInboxKittenClient(unittest.TestCase):
    """InboxKitten provider test"""

    def test_inheritance(self):
        from providers.inboxkitten import InboxkittenClient
        from providers.base import TempMailClient
        self.assertTrue(issubclass(InboxkittenClient, TempMailClient))

    def test_provider_name(self):
        from providers.inboxkitten import InboxkittenClient
        c = InboxkittenClient()
        self.assertEqual(c.provider_name, 'inboxkitten')

    def test_has_methods(self):
        from providers.inboxkitten import InboxkittenClient
        c = InboxkittenClient()
        self.assertTrue(callable(c.generate_email))
        self.assertTrue(callable(c.list_emails))
        self.assertTrue(callable(c.get_email_detail))


class TestMailnesiaClient(unittest.TestCase):
    """Mailnesia provider test"""

    def test_inheritance(self):
        from providers.mailnesia import MailnesiaClient
        from providers.base import TempMailClient
        self.assertTrue(issubclass(MailnesiaClient, TempMailClient))

    def test_provider_name(self):
        from providers.mailnesia import MailnesiaClient
        c = MailnesiaClient()
        self.assertEqual(c.provider_name, 'mailnesia')

    def test_has_methods(self):
        from providers.mailnesia import MailnesiaClient
        c = MailnesiaClient()
        self.assertTrue(callable(c.generate_email))
        self.assertTrue(callable(c.list_emails))
        self.assertTrue(callable(c.get_email_detail))


class TestAnonymmailClient(unittest.TestCase):
    """Anonymmail provider test"""

    def test_inheritance(self):
        from providers.anonymmail import AnonymmailClient
        from providers.base import TempMailClient
        self.assertTrue(issubclass(AnonymmailClient, TempMailClient))

    def test_provider_name(self):
        from providers.anonymmail import AnonymmailClient
        c = AnonymmailClient()
        self.assertEqual(c.provider_name, 'anonymmail')

    def test_has_methods(self):
        from providers.anonymmail import AnonymmailClient
        c = AnonymmailClient()
        self.assertTrue(callable(c.generate_email))
        self.assertTrue(callable(c.list_emails))
        self.assertTrue(callable(c.get_email_detail))


class TestTempMailLolClient(unittest.TestCase):
    """TempMail.lol provider test"""

    def test_inheritance(self):
        from providers.tempmail_lol import TempMailLolClient
        from providers.base import TempMailClient
        self.assertTrue(issubclass(TempMailLolClient, TempMailClient))

    def test_provider_name(self):
        from providers.tempmail_lol import TempMailLolClient
        c = TempMailLolClient()
        self.assertEqual(c.provider_name, 'tempmail.lol')

    def test_has_methods(self):
        from providers.tempmail_lol import TempMailLolClient
        c = TempMailLolClient()
        self.assertTrue(callable(c.generate_email))
        self.assertTrue(callable(c.list_emails))
        self.assertTrue(callable(c.get_email_detail))
