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


class TestChatGPTMailClient(unittest.TestCase):
    """ChatGPTMail provider test"""

    def test_inheritance(self):
        from providers.chatgptmail import ChatGPTMailClient
        from providers.base import TempMailClient
        self.assertTrue(issubclass(ChatGPTMailClient, TempMailClient))

    def test_provider_name(self):
        from providers.chatgptmail import ChatGPTMailClient
        c = ChatGPTMailClient()
        self.assertEqual(c.provider_name, 'chatgptmail')

    def test_has_methods(self):
        from providers.chatgptmail import ChatGPTMailClient
        c = ChatGPTMailClient()
        self.assertTrue(callable(c.generate_email))
        self.assertTrue(callable(c.list_emails))
        self.assertTrue(callable(c.get_email_detail))


class TestTempMailIngClient(unittest.TestCase):
    """TempMail.ing provider test"""

    def test_inheritance(self):
        from providers.tempmail_ing import TempMailIngClient
        from providers.base import TempMailClient
        self.assertTrue(issubclass(TempMailIngClient, TempMailClient))

    def test_provider_name(self):
        from providers.tempmail_ing import TempMailIngClient
        c = TempMailIngClient()
        self.assertEqual(c.provider_name, 'tempmail.ing')

    def test_has_methods(self):
        from providers.tempmail_ing import TempMailIngClient
        c = TempMailIngClient()
        self.assertTrue(callable(c.generate_email))
        self.assertTrue(callable(c.list_emails))
        self.assertTrue(callable(c.get_email_detail))


class TestEmailTickClient(unittest.TestCase):
    """EmailTick provider test"""

    def test_inheritance(self):
        from providers.emailtick import EmailTickClient
        from providers.base import TempMailClient
        self.assertTrue(issubclass(EmailTickClient, TempMailClient))

    def test_provider_name(self):
        from providers.emailtick import EmailTickClient
        c = EmailTickClient()
        self.assertEqual(c.provider_name, 'emailtick')

    def test_has_methods(self):
        from providers.emailtick import EmailTickClient
        c = EmailTickClient()
        self.assertTrue(callable(c.generate_email))
        self.assertTrue(callable(c.list_emails))
        self.assertTrue(callable(c.get_email_detail))
        self.assertTrue(callable(c.delete_email))

    def test_parse_emailtick_html_rows(self):
        from providers.emailtick import EmailTickClient
        c = EmailTickClient()
        html = '''
        <div class="msglist"><table><tbody>
        <tr>
          <td>sender@example.com</td>
          <td><a href="/mail/abc123">Verify account</a></td>
          <td>2026-06-20 16:00</td>
        </tr>
        </tbody></table></div>
        '''
        parsed = c._parse_emails(html)
        self.assertEqual(len(parsed), 1)
        self.assertTrue(parsed[0]['id'])
        self.assertEqual(parsed[0]['subject'], 'Verify account')
        self.assertEqual(parsed[0]['from_email'], 'sender@example.com')
        self.assertEqual(parsed[0]['received_at'], '2026-06-20 16:00')
        self.assertEqual(parsed[0]['href'], '/mail/abc123')

    def test_change_email_posts_expected_payload(self):
        from providers.emailtick import EmailTickClient
        c = EmailTickClient()
        c._mailbox = 'old@gmail.com'
        c._salt = 'salt'
        c._fetch_page = MagicMock(return_value='')
        c._activate = MagicMock(return_value=True)
        response = MagicMock()
        response.text = 'new@gmail.com'
        response.raise_for_status = MagicMock()
        c.session.post = MagicMock(return_value=response)

        email = c.change_email(random=True)

        self.assertEqual(email.address, 'new@gmail.com')
        c.session.post.assert_called_once()
        payload = c.session.post.call_args.kwargs['data']
        self.assertEqual(payload['type[]'], ['1', '2', '3'])
        self.assertEqual(payload['set'], '1')
