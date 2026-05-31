"""
Provider 客户端模拟测试（不需要网络）
运行: python -m pytest tests/test_providers_mock.py -v
"""

import json
import unittest
from unittest.mock import MagicMock, patch, PropertyMock

from providers.base import InboxEmail, TempEmail, TempMailClient
from providers.utils import (
    ETagCache,
    EmailFetchError,
    EmailGenerateError,
    RateLimitError,
    TempMailError,
    retry,
)


class TestBoomlifyDecrypt(unittest.TestCase):
    """Boomlify XOR 解密测试"""

    def test_xor_roundtrip(self):
        from providers.boomlify import _xor_decrypt, ENCRYPTION_KEY
        original = '{"token":"abc123"}'
        key_bytes = ENCRYPTION_KEY.encode("utf-8")
        orig_bytes = original.encode("utf-8")
        encrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(orig_bytes))
        result = _xor_decrypt(encrypted.hex(), ENCRYPTION_KEY)
        self.assertEqual(result, original)

    def test_decrypt_response_passthrough(self):
        from providers.boomlify import _decrypt_response
        data = {"status": "ok"}
        self.assertEqual(_decrypt_response(data), data)

    def test_decrypt_with_transport_key(self):
        from providers.boomlify import _decrypt_response, TRANSPORT_KEY_RING
        key = TRANSPORT_KEY_RING["qwert"]
        original = '{"hello":"world"}'
        key_bytes = key.encode("utf-8")
        orig_bytes = original.encode("utf-8")
        encrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(orig_bytes))
        data = {"encrypted": encrypted.hex()}
        result = _decrypt_response(data, key_id="qwert")
        self.assertEqual(result, {"hello": "world"})


class TestETagCacheAdvanced(unittest.TestCase):
    """ETag 缓存高级测试"""

    def test_overwrite(self):
        cache = ETagCache(ttl_seconds=60)
        cache.put("k", "etag1")
        cache.put("k", "etag2")
        self.assertEqual(cache.get("k"), "etag2")

    def test_stats_empty(self):
        cache = ETagCache(ttl_seconds=60)
        stats = cache.stats()
        self.assertEqual(stats["cached_keys"], 0)
        self.assertEqual(stats["hit_rate"], "0.0%")

    def test_invalidate_nonexistent(self):
        cache = ETagCache(ttl_seconds=60)
        cache.invalidate("no_such_key")  # should not raise


class TestRetryAdvanced(unittest.TestCase):
    """重试装饰器高级测试"""

    def test_retry_with_partial_failures(self):
        calls = []

        @retry(max_attempts=5, backoff_factor=0.001, exceptions=(ValueError,))
        def flaky():
            calls.append(1)
            if len(calls) < 4:
                raise ValueError("transient")
            return "ok"

        self.assertEqual(flaky(), "ok")
        self.assertEqual(len(calls), 4)

    def test_retry_preserves_args(self):
        @retry(max_attempts=2, backoff_factor=0.001)
        def add(a, b):
            return a + b

        self.assertEqual(add(3, 4), 7)


class TestBaseModelsAdvanced(unittest.TestCase):
    """数据模型高级测试"""

    def test_temp_email_with_all_fields(self):
        email = TempEmail(
            address="test@example.com",
            provider="test",
            expires_at="2026-01-01T00:00:00Z",
            created_at="2025-12-31T23:50:00Z",
            duration_minutes=10,
            raw={"key": "value"},
        )
        self.assertEqual(email.address, "test@example.com")
        self.assertEqual(email.duration_minutes, 10)
        self.assertEqual(email.raw, {"key": "value"})

    def test_inbox_email_with_all_fields(self):
        email = InboxEmail(
            id="123",
            provider="test",
            subject="Hello",
            from_email="sender@example.com",
            from_name="Sender",
            body_html="<b>Hi</b>",
            body_text="Hi",
            received_at="2026-01-01T00:00:00Z",
        )
        self.assertEqual(email.subject, "Hello")
        self.assertEqual(email.from_name, "Sender")
        self.assertIn("<b>", email.body_html)

    def test_temp_email_str(self):
        email = TempEmail(address="test@example.com", provider="test")
        self.assertEqual(str(email), "test@example.com (test)")

    def test_inbox_email_str(self):
        email = InboxEmail(id="1", provider="test", subject="Hello", from_name="Alice")
        self.assertEqual(str(email), "[test] Hello - Alice")

    def test_inbox_email_str_no_subject(self):
        email = InboxEmail(id="1", provider="test", from_email="bob@test.com")
        self.assertEqual(str(email), "[test] (无主题) - bob@test.com")

    def test_temp_email_to_dict(self):
        email = TempEmail(address="a@b.com", provider="test", duration_minutes=10)
        d = email.to_dict()
        self.assertEqual(d["address"], "a@b.com")
        self.assertEqual(d["duration_minutes"], 10)

    def test_inbox_email_to_dict(self):
        email = InboxEmail(id="1", provider="test", subject="Hi")
        d = email.to_dict()
        self.assertEqual(d["id"], "1")
        self.assertEqual(d["subject"], "Hi")


class TestChatGPTMailClientMock(unittest.TestCase):
    """ChatGPTMail 客户端模拟测试"""

    @patch("providers.chatgptmail.curl_requests")
    def test_provider_name(self, mock_requests):
        from providers.chatgptmail import ChatGPTMailClient
        client = ChatGPTMailClient()
        self.assertEqual(client.provider_name, "chatgptmail")

    @patch("providers.chatgptmail.curl_requests")
    def test_generate_email_success(self, mock_requests):
        from providers.chatgptmail import ChatGPTMailClient

        # Mock 首页响应
        mock_home = MagicMock()
        mock_home.text = 'window.__BROWSER_AUTH = {"token": "test-token-123"};'
        mock_home.raise_for_status = MagicMock()

        # Mock 生成邮箱响应
        mock_generate = MagicMock()
        mock_generate.json.return_value = {
            "success": True,
            "data": {"email": "abc123@mail.chatgpt.org.uk"},
            "auth": {"token": "inbox-token-456"},
        }
        mock_generate.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_home
        mock_session.post.return_value = mock_generate
        mock_requests.Session.return_value = mock_session

        client = ChatGPTMailClient()
        email = client.generate_email()
        self.assertEqual(email.address, "abc123@mail.chatgpt.org.uk")
        self.assertEqual(email.provider, "chatgptmail")

    @patch("providers.chatgptmail.curl_requests")
    def test_generate_email_failure(self, mock_requests):
        from providers.chatgptmail import ChatGPTMailClient

        mock_home = MagicMock()
        mock_home.text = 'window.__BROWSER_AUTH = {"token": "test-token"};'
        mock_home.raise_for_status = MagicMock()

        mock_generate = MagicMock()
        mock_generate.json.return_value = {"success": False, "error": "rate limited"}
        mock_generate.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_home
        mock_session.post.return_value = mock_generate
        mock_requests.Session.return_value = mock_session

        client = ChatGPTMailClient()
        with self.assertRaises(EmailGenerateError):
            client.generate_email()


class TestGuerrillaMailClientMock(unittest.TestCase):
    """GuerrillaMail 客户端模拟测试"""

    def test_provider_name(self):
        from providers.guerrillamail import GuerrillaMailClient
        client = GuerrillaMailClient()
        self.assertEqual(client.provider_name, "guerrillamail")

    @patch("providers.guerrillamail.requests")
    def test_generate_email(self, mock_requests):
        from providers.guerrillamail import GuerrillaMailClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "sid_token": "test-sid",
            "email_addr": "test@guerrillamail.com",
        }
        mock_resp.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_requests.Session.return_value = mock_session

        client = GuerrillaMailClient()
        client._sid_token = "test-sid"
        client._email_addr = "test@guerrillamail.com"
        email = client.generate_email()
        self.assertIn("@", email.address)

    @patch("providers.guerrillamail.requests")
    def test_list_emails(self, mock_requests):
        from providers.guerrillamail import GuerrillaMailClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "list": [
                {
                    "mail_id": 1,
                    "mail_subject": "Test Subject",
                    "mail_from": "sender@example.com",
                    "mail_excerpt": "Hello world",
                    "mail_date": "2026-01-01 00:00:00",
                },
                {
                    "mail_id": 0,  # 无效邮件，应被过滤
                    "mail_subject": "",
                    "mail_from": "",
                },
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_requests.Session.return_value = mock_session

        client = GuerrillaMailClient()
        client._sid_token = "test-sid"
        emails = client.list_emails("test@guerrillamail.com")
        self.assertEqual(len(emails), 1)  # mail_id=0 被过滤
        self.assertEqual(emails[0].subject, "Test Subject")


if __name__ == "__main__":
    unittest.main()


class TestMailTmClientMock(unittest.TestCase):
    """Mail.tm 客户端模拟测试"""

    def test_provider_name(self):
        from providers.mail_tm import MailTmClient
        client = MailTmClient()
        self.assertEqual(client.provider_name, "mail.tm")

    @patch("providers.mail_tm.requests")
    def test_generate_email(self, mock_requests):
        from providers.mail_tm import MailTmClient

        mock_domains = MagicMock()
        mock_domains.json.return_value = {
            "hydra:member": [{"domain": "mail.tm"}]
        }
        mock_domains.raise_for_status = MagicMock()

        mock_account = MagicMock()
        mock_account.json.return_value = {
            "id": "acc-123",
            "address": "testuser@mail.tm",
        }
        mock_account.raise_for_status = MagicMock()

        mock_token = MagicMock()
        mock_token.json.return_value = {"token": "jwt-token-123"}
        mock_token.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.request.side_effect = [mock_domains, mock_account, mock_token]
        mock_requests.Session.return_value = mock_session

        client = MailTmClient()
        email = client.generate_email()
        self.assertIn("@mail.tm", email.address)
        self.assertEqual(email.provider, "mail.tm")

    @patch("providers.mail_tm.requests")
    def test_list_emails(self, mock_requests):
        from providers.mail_tm import MailTmClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "hydra:member": [
                {
                    "id": "msg-1",
                    "subject": "Test Subject",
                    "from": {"address": "sender@example.com", "name": "Sender"},
                    "intro": "Hello world",
                    "createdAt": "2026-01-01T00:00:00Z",
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()
        mock_resp.status_code = 200

        mock_session = MagicMock()
        mock_session.request.return_value = mock_resp
        mock_requests.Session.return_value = mock_session

        client = MailTmClient()
        client._token = "test-token"
        emails = client.list_emails("test@mail.tm")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Test Subject")
        self.assertEqual(emails[0].from_email, "sender@example.com")

    @patch("providers.mail_tm.requests")
    def test_delete_email(self, mock_requests):
        from providers.mail_tm import MailTmClient

        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_resp.status_code = 204

        mock_session = MagicMock()
        mock_session.request.return_value = mock_resp
        mock_requests.Session.return_value = mock_session

        client = MailTmClient()
        client._token = "test-token"
        result = client.delete_email("msg-1")
        self.assertTrue(result)


class TestEmailnatorClientMock(unittest.TestCase):
    """Emailnator 客户端模拟测试"""

    def test_provider_name(self):
        from providers.emailnator import EmailnatorClient
        client = EmailnatorClient()
        self.assertEqual(client.provider_name, "emailnator")

    @patch("providers.emailnator.requests")
    def test_generate_email(self, mock_requests):
        from providers.emailnator import EmailnatorClient

        mock_home = MagicMock()
        mock_home.raise_for_status = MagicMock()

        mock_gen = MagicMock()
        mock_gen.json.return_value = {"email": ["testuser@gmail.com"]}
        mock_gen.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_home
        mock_session.post.return_value = mock_gen

        mock_requests.Session.return_value = mock_session

        client = EmailnatorClient()
        email = client.generate_email()
        self.assertIn("@gmail.com", email.address)
        self.assertEqual(email.provider, "emailnator")

    @patch("providers.emailnator.requests")
    def test_list_emails(self, mock_requests):
        from providers.emailnator import EmailnatorClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "messageData": [
                {
                    "messageID": "msg-1",
                    "subject": "Verification Code",
                    "from": "noreply@example.com",
                    "textContent": "Your code is 123456",
                    "date": "2026-01-01 00:00:00",
                }
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp
        mock_requests.Session.return_value = mock_session

        client = EmailnatorClient()
        client._current_email = "test@gmail.com"
        emails = client.list_emails("test@gmail.com")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Verification Code")


class TestTempMailOrgClientMock(unittest.TestCase):
    """Temp-Mail.org 客户端模拟测试"""

    def test_provider_name(self):
        from providers.tempmail_org import TempMailOrgClient
        client = TempMailOrgClient()
        self.assertEqual(client.provider_name, "temp-mail.org")

    @patch("providers.tempmail_org.requests")
    def test_generate_email(self, mock_requests):
        from providers.tempmail_org import TempMailOrgClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"mailbox": "abc123@mail.com", "token": "tok-xyz"}
        mock_resp.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.post.return_value = mock_resp
        mock_requests.Session.return_value = mock_session

        client = TempMailOrgClient()
        email = client.generate_email()
        self.assertEqual(email.address, "abc123@mail.com")
        self.assertEqual(email.provider, "temp-mail.org")

    @patch("providers.tempmail_org.requests")
    def test_list_emails(self, mock_requests):
        from providers.tempmail_org import TempMailOrgClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "messages": [
                {"_id": "m1", "subject": "Hello", "from": "a@b.com", "bodyPreview": "Hi there"}
            ]
        }
        mock_resp.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.return_value = mock_resp
        mock_requests.Session.return_value = mock_session

        client = TempMailOrgClient()
        client._token = "tok-xyz"
        emails = client.list_emails("abc@mail.com")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Hello")


class TestYopmailClientMock(unittest.TestCase):
    """Yopmail 客户端模拟测试"""

    def test_provider_name(self):
        from providers.yopmail import YopmailClient
        client = YopmailClient()
        self.assertEqual(client.provider_name, "yopmail")

    @patch("providers.yopmail.requests")
    def test_generate_email(self, mock_requests):
        from providers.yopmail import YopmailClient

        # Mock the homepage response
        mock_home = MagicMock()
        mock_home.text = '<html><input name="yp" id="yp" value="abc123" /><script src="/ver/9.0/webmail.js"></script></html>'
        mock_home.raise_for_status = MagicMock()

        # Mock the webmail.js response
        mock_js = MagicMock()
        mock_js.text = "value+'&yj=XYZ789&v='"
        mock_js.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.side_effect = [mock_home, mock_js]
        mock_requests.Session.return_value = mock_session

        client = YopmailClient()
        email = client.generate_email()
        self.assertIn("@yopmail.com", email.address)
        self.assertEqual(email.provider, "yopmail")

    @patch("providers.yopmail.requests")
    def test_list_emails_empty(self, mock_requests):
        from providers.yopmail import YopmailClient

        mock_home = MagicMock()
        mock_home.text = '<html><input name="yp" id="yp" value="abc123" /><script src="/ver/9.0/webmail.js"></script></html>'
        mock_home.raise_for_status = MagicMock()

        mock_js = MagicMock()
        mock_js.text = "value+'&yj=XYZ789&v='"
        mock_js.raise_for_status = MagicMock()

        mock_inbox = MagicMock()
        mock_inbox.text = '<html><tbody></tbody></html>'
        mock_inbox.raise_for_status = MagicMock()

        mock_session = MagicMock()
        mock_session.get.side_effect = [mock_home, mock_js, mock_inbox]
        mock_session.cookies = MagicMock()
        mock_requests.Session.return_value = mock_session

        client = YopmailClient()
        client._yp = "abc"
        client._yj = "xyz"
        client._username = "testuser"
        client._version = "9.0"
        emails = client.list_emails("testuser@yopmail.com")
        self.assertEqual(len(emails), 0)


class TestTempMailLolClientMock(unittest.TestCase):
    """TempMail.lol 客户端模拟测试"""

    def test_provider_name(self):
        from providers.tempmail_lol import TempMailLolClient
        client = TempMailLolClient()
        self.assertEqual(client.provider_name, "tempmail.lol")

    @patch("providers.tempmail_lol.requests")
    def test_generate_email(self, mock_requests):
        from providers.tempmail_lol import TempMailLolClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {"address": "abc@tmpmail.cc", "token": "tok-123"}
        mock_resp.raise_for_status = MagicMock()
        mock_resp.status_code = 200

        mock_session = MagicMock()
        mock_session.request.return_value = mock_resp
        mock_requests.Session.return_value = mock_session

        client = TempMailLolClient()
        email = client.generate_email()
        self.assertEqual(email.address, "abc@tmpmail.cc")
        self.assertEqual(email.provider, "tempmail.lol")

    @patch("providers.tempmail_lol.requests")
    def test_list_emails(self, mock_requests):
        from providers.tempmail_lol import TempMailLolClient

        mock_resp = MagicMock()
        mock_resp.json.return_value = {
            "expired": False,
            "emails": [
                {"from": "a@b.com", "subject": "Test", "body": "Hello", "html": "<p>Hello</p>", "date": 1700000000000}
            ],
        }
        mock_resp.raise_for_status = MagicMock()
        mock_resp.status_code = 200

        mock_session = MagicMock()
        mock_session.request.return_value = mock_resp
        mock_requests.Session.return_value = mock_session

        client = TempMailLolClient()
        client._token = "tok-123"
        emails = client.list_emails("abc@tmpmail.cc")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Test")
        self.assertEqual(emails[0].from_email, "a@b.com")

    def test_rate_limit_error(self):
        from providers.tempmail_lol import TempMailLolClient
        from providers.utils import EmailGenerateError

        client = TempMailLolClient()
        # Verify rate limit raises proper error
        with patch.object(client.session, "request") as mock_req:
            mock_resp = MagicMock()
            mock_resp.status_code = 429
            mock_resp.text = "Rate limited"
            mock_req.return_value = mock_resp
            with self.assertRaises(EmailGenerateError):
                client.generate_email()


class TestMailGwClient(unittest.TestCase):
    """Mail.gw provider 测试"""

    @patch("providers.mail_gw.MailGwClient._get_domains", return_value=["mail.gw"])
    @patch("providers.mail_gw.MailGwClient._create_account", return_value={"id": "1"})
    @patch("providers.mail_gw.MailGwClient._get_token", return_value="tok-123")
    def test_generate_email(self, *args):
        from providers.mail_gw import MailGwClient
        client = MailGwClient()
        email = client.generate_email()
        self.assertIn("@mail.gw", email.address)
        self.assertEqual(email.provider, "mail.gw")

    def test_list_emails(self):
        from providers.mail_gw import MailGwClient
        client = MailGwClient()
        client._token = "tok-123"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "hydra:member": [
                {"id": "1", "from": {"address": "a@b.com"}, "subject": "Hi", "createdAt": "2024-01-01", "text": "Hello"}
            ]
        }
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@mail.gw")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Hi")


class TestHarakirimailClient(unittest.TestCase):
    """Harakirimail provider 测试"""

    def test_generate_email(self):
        from providers.harakirimail import HarakirimailClient

        client = HarakirimailClient()
        email = client.generate_email()
        self.assertIn("@harakirimail.com", email.address)
        self.assertEqual(email.provider, "harakirimail")

    def test_list_emails(self):
        from providers.harakirimail import HarakirimailClient
        client = HarakirimailClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "emails": [{"_id": "1", "from": "a@b.com", "subject": "Test", "received": 1700000000}]
        }
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@harakirimail.com")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Test")


class TestTempMailPlusClient(unittest.TestCase):
    """TempMail.plus provider 测试"""

    def test_generate_email(self):
        from providers.tempmail_plus import TempMailPlusClient

        client = TempMailPlusClient()
        email = client.generate_email()
        self.assertIn("@", email.address)
        self.assertEqual(email.provider, "tempmail.plus")

    def test_list_emails(self):
        from providers.tempmail_plus import TempMailPlusClient
        client = TempMailPlusClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "mail_list": [{"mail_id": "1", "from": "a@b.com", "subject": "Test", "time": 1700000000}]
        }
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@mailto.plus")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Test")


class TestInboxesClient(unittest.TestCase):
    """Inboxes.com provider 测试"""

    @patch("providers.inboxes.InboxesClient._get_domains", return_value=["inboxes.com"])
    def test_generate_email(self, *args):
        from providers.inboxes import InboxesClient

        client = InboxesClient()
        email = client.generate_email()
        self.assertIn("@inboxes.com", email.address)
        self.assertEqual(email.provider, "inboxes.com")

    def test_list_emails(self):
        from providers.inboxes import InboxesClient
        client = InboxesClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "msgs": [{"uid": "1", "f": "a@b.com", "s": "Test", "cr": 1700000000, "ph": "Preview"}]
        }
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@inboxes.com")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Test")


class TestNoopmailClient(unittest.TestCase):
    """Noopmail.org provider test"""

    @patch("providers.noopmail.NoopmailClient._get_domains", return_value=["noopmail.org"])
    def test_generate_email(self, *args):
        from providers.noopmail import NoopmailClient
        client = NoopmailClient()
        email = client.generate_email()
        self.assertIn("@noopmail.org", email.address)
        self.assertEqual(email.provider, "noopmail")

    def test_list_emails(self):
        from providers.noopmail import NoopmailClient
        client = NoopmailClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": "1", "from": "a@b.com", "subject": "Test", "date": 1700000000, "text": "Hi"}
        ]
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        emails = client.list_emails("test@noopmail.org")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Test")


class TestMailnesiaClient(unittest.TestCase):
    """Mailnesia.com provider test"""

    def test_generate_email(self):
        from providers.mailnesia import MailnesiaClient
        client = MailnesiaClient()
        email = client.generate_email()
        self.assertIn("@mailnesia.com", email.address)
        self.assertEqual(email.provider, "mailnesia")

    def test_list_emails_empty(self):
        from providers.mailnesia import MailnesiaClient
        client = MailnesiaClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><body><table></table></body></html>'
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@mailnesia.com")
        self.assertEqual(len(emails), 0)


class TestMoaktClient(unittest.TestCase):
    """Moakt.com provider test"""

    @patch("providers.moakt.MoaktClient._get_domains", return_value=["mocake.com"])
    def test_generate_email(self, *args):
        from providers.moakt import MoaktClient
        client = MoaktClient()
        email = client.generate_email()
        self.assertIn("@mocake.com", email.address)
        self.assertEqual(email.provider, "moakt")

    def test_list_emails_empty(self):
        from providers.moakt import MoaktClient
        client = MoaktClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><body><div id="email_message_list"></div></body></html>'
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@mocake.com")
        self.assertIsInstance(emails, list)


class TestFakemailNetClient(unittest.TestCase):
    """Fakemail.net provider test"""

    def test_provider_name(self):
        from providers.fakemail_net import FakemailNetClient
        client = FakemailNetClient()
        self.assertEqual(client.provider_name, "fakemail.net")

    def test_generate_email(self):
        from providers.fakemail_net import FakemailNetClient
        client = FakemailNetClient()
        mock_resp1 = MagicMock()
        mock_resp1.status_code = 200
        mock_resp1.text = 'const CSRF="abc123"'
        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_resp2.content = b'{"email":"test@fakemail.net"}'
        client._session = MagicMock()
        client._session.get.side_effect = [mock_resp1, mock_resp2]
        email = client.generate_email()
        self.assertEqual(email.address, "test@fakemail.net")
        self.assertEqual(email.provider, "fakemail.net")

    def test_list_emails_empty(self):
        from providers.fakemail_net import FakemailNetClient
        client = FakemailNetClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><body><table></table></body></html>'
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@fakemail.net")
        self.assertIsInstance(emails, list)


class TestEmailfakeClient(unittest.TestCase):
    """Emailfake.com provider test"""

    @patch("providers.emailfake.EmailfakeClient._get_domains", return_value=["tmpeml.com"])
    def test_generate_email(self, *args):
        from providers.emailfake import EmailfakeClient
        client = EmailfakeClient()
        email = client.generate_email()
        self.assertIn("@tmpeml.com", email.address)
        self.assertEqual(email.provider, "emailfake")

    def test_list_emails_empty(self):
        from providers.emailfake import EmailfakeClient
        client = EmailfakeClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><body><div id="email-table"></div></body></html>'
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@tmpeml.com")
        self.assertIsInstance(emails, list)


class TestTempomailClient(unittest.TestCase):
    """Tempomail.top provider test"""

    def test_provider_name(self):
        from providers.tempomail import TempomailClient
        client = TempomailClient()
        self.assertEqual(client.provider_name, "tempomail")

    def test_generate_email(self):
        from providers.tempomail import TempomailClient
        client = TempomailClient()
        client._apikey = "test-key"
        client._session = MagicMock()
        # domains call
        mock_domains = MagicMock()
        mock_domains.status_code = 200
        mock_domains.json.return_value = {"body": {"data": {"domains": [{"name": "tempomail.top"}]}}}
        # create call
        mock_create = MagicMock()
        mock_create.status_code = 200
        mock_create.json.return_value = {}
        client._session.get.return_value = mock_domains
        client._session.post.return_value = mock_create
        email = client.generate_email()
        self.assertIn("@tempomail.top", email.address)
        self.assertEqual(email.provider, "tempomail")

    def test_list_emails(self):
        from providers.tempomail import TempomailClient
        client = TempomailClient()
        client._apikey = "test-key"
        client._session = MagicMock()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "body": {"data": {"messages": {"rows": [
                {"id": "1", "from": "a@b.com", "subject": "Test", "date": "2025-01-01"}
            ]}}}
        }
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@tempomail.top")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Test")


class TestAnonymmailClient(unittest.TestCase):
    """Anonymmail.net provider test"""

    def test_provider_name(self):
        from providers.anonymmail import AnonymmailClient
        client = AnonymmailClient()
        self.assertEqual(client.provider_name, "anonymmail")

    @patch("providers.anonymmail.AnonymmailClient._get_domains", return_value=["anonymmail.net"])
    def test_generate_email(self, *args):
        from providers.anonymmail import AnonymmailClient
        client = AnonymmailClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"success": True}
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        email = client.generate_email()
        self.assertIn("@anonymmail.net", email.address)
        self.assertEqual(email.provider, "anonymmail")


class TestEmailondeckClient(unittest.TestCase):
    """Emailondeck.com provider test"""

    def test_generate_email(self):
        from providers.emailondeck import EmailondeckClient
        client = EmailondeckClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "test@emailondeck.com|token123"
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        email = client.generate_email()
        self.assertEqual(email.address, "test@emailondeck.com")
        self.assertEqual(email.provider, "emailondeck")


class TestEtempmailClient(unittest.TestCase):
    """Etempmail.com provider test"""

    def test_generate_email(self):
        from providers.etempmail import EtempmailClient
        client = EtempmailClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"address": "test@etempmail.com"}
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        email = client.generate_email()
        self.assertEqual(email.address, "test@etempmail.com")
        self.assertEqual(email.provider, "etempmail")


class TestTempmClient(unittest.TestCase):
    """Tempm.com provider test"""

    @patch("providers.tempm.TempmClient._get_domains", return_value=["royal.net"])
    def test_generate_email(self, *args):
        from providers.tempm import TempmClient
        client = TempmClient()
        email = client.generate_email()
        self.assertIn("@royal.net", email.address)
        self.assertEqual(email.provider, "tempm")


class TestGeneratorEmailClient(unittest.TestCase):
    """Generator.email provider test"""

    @patch("providers.generator_email.GeneratorEmailClient._get_domains", return_value=["tmpeml.com"])
    def test_generate_email(self, *args):
        from providers.generator_email import GeneratorEmailClient
        client = GeneratorEmailClient()
        email = client.generate_email()
        self.assertIn("@tmpeml.com", email.address)
        self.assertEqual(email.provider, "generator.email")


class TestEmaildashfakeClient(unittest.TestCase):
    """Email-fake.com provider test"""

    @patch("providers.emaildashfake.EmaildashfakeClient._get_domains", return_value=["tmpeml.com"])
    def test_generate_email(self, *args):
        from providers.emaildashfake import EmaildashfakeClient
        client = EmaildashfakeClient()
        email = client.generate_email()
        self.assertIn("@tmpeml.com", email.address)
        self.assertEqual(email.provider, "email-fake")


class TestAdguardClient(unittest.TestCase):
    """Adguard tempmail provider test"""

    def test_provider_name(self):
        from providers.adguard import AdguardClient
        client = AdguardClient()
        self.assertEqual(client.provider_name, "adguard")

    def test_generate_email(self):
        from providers.adguard import AdguardClient
        client = AdguardClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = "copyEmailAddress('test@adguard.com')"
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        email = client.generate_email()
        self.assertEqual(email.address, "test@adguard.com")
        self.assertEqual(email.provider, "adguard")

    def test_list_emails(self):
        from providers.adguard import AdguardClient
        client = AdguardClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"emails": [
            {"message_id": "1", "from": [{"address": "a@b.com"}], "subject": "Test", "time_added_timestamp": 1700000000, "content_html": "<p>Hi</p>"}
        ]}
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@adguard.com")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Test")


class TestInboxkittenClient(unittest.TestCase):
    """InboxKitten.com provider test"""

    def test_provider_name(self):
        from providers.inboxkitten import InboxkittenClient
        client = InboxkittenClient()
        self.assertEqual(client.provider_name, "inboxkitten")

    def test_generate_email(self):
        from providers.inboxkitten import InboxkittenClient
        client = InboxkittenClient()
        email = client.generate_email()
        self.assertIn("@inboxkitten.com", email.address)
        self.assertEqual(email.provider, "inboxkitten")

    def test_list_emails(self):
        from providers.inboxkitten import InboxkittenClient
        client = InboxkittenClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"storage": {"region": "us", "key": "123"}, "message": {"headers": {"from": "a@b.com", "subject": "Test"}}, "timestamp": 1700000000}
        ]
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@inboxkitten.com")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].id, "us,123")


class TestDisposablemailClient(unittest.TestCase):
    """Disposablemail.com provider test"""

    def test_provider_name(self):
        from providers.disposablemail import DisposablemailClient
        client = DisposablemailClient()
        self.assertEqual(client.provider_name, "disposablemail")

    def test_generate_email(self):
        from providers.disposablemail import DisposablemailClient
        client = DisposablemailClient()
        mock_resp1 = MagicMock()
        mock_resp1.status_code = 200
        mock_resp1.text = 'const CSRF="abc123"'
        mock_resp2 = MagicMock()
        mock_resp2.status_code = 200
        mock_resp2.content = b'{"email":"test@disposablemail.com"}'
        client._session = MagicMock()
        client._session.get.side_effect = [mock_resp1, mock_resp2]
        email = client.generate_email()
        self.assertEqual(email.address, "test@disposablemail.com")
        self.assertEqual(email.provider, "disposablemail")


class TestFakemailgeneratorClient(unittest.TestCase):
    """Fakemailgenerator.com provider test"""

    @patch("providers.fakemailgenerator.FakemailgeneratorClient._get_domains", return_value=["yuoia.com"])
    def test_generate_email(self, *args):
        from providers.fakemailgenerator import FakemailgeneratorClient
        client = FakemailgeneratorClient()
        email = client.generate_email()
        self.assertIn("@yuoia.com", email.address)
        self.assertEqual(email.provider, "fakemailgenerator")


class TestTrashmailClient(unittest.TestCase):
    """Trashmail.com provider test"""

    @patch("providers.trashmail.TrashmailClient._get_domains", return_value=["trash-mail.com"])
    def test_generate_email(self, *args):
        from providers.trashmail import TrashmailClient
        client = TrashmailClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        email = client.generate_email()
        self.assertIn("@trash-mail.com", email.address)
        self.assertEqual(email.provider, "trashmail")


class TestOnesecmailClient(unittest.TestCase):
    """1SecMail.com provider test"""

    @patch("providers.onesecmail.OnesecmailClient._get_domains", return_value=["1secmail.com"])
    def test_generate_email(self, *args):
        from providers.onesecmail import OnesecmailClient
        client = OnesecmailClient()
        email = client.generate_email()
        self.assertIn("@1secmail.com", email.address)
        self.assertEqual(email.provider, "1secmail")

    def test_list_emails(self):
        from providers.onesecmail import OnesecmailClient
        client = OnesecmailClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": 1, "from": "a@b.com", "subject": "Test", "date": "2025-01-01"}
        ]
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@1secmail.com")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Test")

    def test_get_email_detail(self):
        from providers.onesecmail import OnesecmailClient
        client = OnesecmailClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "id": 1, "from": "a@b.com", "subject": "Test", "date": "2025-01-01",
            "body": "<p>Hi</p>", "textBody": "Hi"
        }
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        detail = client.get_email_detail("test@1secmail.com", "1")
        self.assertIsNotNone(detail)
        self.assertEqual(detail.subject, "Test")
        self.assertEqual(detail.body_html, "<p>Hi</p>")


class TestMaildaxClient(unittest.TestCase):
    """Maildax.com provider test"""

    def test_generate_email(self):
        from providers.maildax import MaildaxClient
        client = MaildaxClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"email": "test@maildax.com", "secret": "sec123"}
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        email = client.generate_email()
        self.assertEqual(email.address, "test@maildax.com")
        self.assertEqual(email.provider, "maildax")


class TestFakermailClient(unittest.TestCase):
    """Fakermail.com provider test"""

    @patch("providers.fakermail.FakermailClient._get_domains", return_value=["fakermail.com"])
    def test_generate_email(self, *args):
        from providers.fakermail import FakermailClient
        client = FakermailClient()
        email = client.generate_email()
        self.assertIn("@fakermail.com", email.address)
        self.assertEqual(email.provider, "fakermail")


class TestMintemailClient(unittest.TestCase):
    """MintEmail.com provider test"""

    def test_provider_name(self):
        from providers.mintemail import MintemailClient
        client = MintemailClient()
        self.assertEqual(client.provider_name, "mintemail")

    def test_generate_email(self):
        from providers.mintemail import MintemailClient
        client = MintemailClient()
        email = client.generate_email()
        self.assertIn("@cj.MintEmail.com", email.address)
        self.assertEqual(email.provider, "mintemail")

    def test_list_emails_empty(self):
        from providers.mintemail import MintemailClient
        client = MintemailClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = " "
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@cj.MintEmail.com")
        self.assertEqual(len(emails), 0)

    def test_list_emails_with_ids(self):
        from providers.mintemail import MintemailClient
        client = MintemailClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = ",123,456"
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@cj.MintEmail.com")
        self.assertEqual(len(emails), 2)
        self.assertEqual(emails[0].id, "123")


class TestEztempmailClient(unittest.TestCase):
    """Eztempmail.com provider test"""

    def test_provider_name(self):
        from providers.eztempmail import EztempmailClient
        client = EztempmailClient()
        self.assertEqual(client.provider_name, "eztempmail")


class TestTmailGgClient(unittest.TestCase):
    """Tmail.gg provider test"""

    def test_provider_name(self):
        from providers.tmail_gg import TmailGgClient
        client = TmailGgClient()
        self.assertEqual(client.provider_name, "tmail.gg")

    @patch("providers.tmail_gg.TmailGgClient._get_domains", return_value=["tmail.gg"])
    def test_generate_email(self, *args):
        from providers.tmail_gg import TmailGgClient
        client = TmailGgClient()
        client._token = "test-token"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        email = client.generate_email()
        self.assertIn("@tmail.gg", email.address)
        self.assertEqual(email.provider, "tmail.gg")


class TestTempemailCoClient(unittest.TestCase):
    """Tempemail.co provider test"""

    def test_provider_name(self):
        from providers.tempemail_co import TempemailCoClient
        client = TempemailCoClient()
        self.assertEqual(client.provider_name, "tempemail.co")

    @patch("providers.tempemail_co.TempemailCoClient._get_domains", return_value=["tempemail.co"])
    def test_generate_email(self, *args):
        from providers.tempemail_co import TempemailCoClient
        client = TempemailCoClient()
        email = client.generate_email()
        self.assertIn("@tempemail.co", email.address)
        self.assertEqual(email.provider, "tempemail.co")


class TestMailgolemClient(unittest.TestCase):
    """Mailgolem.com provider test"""

    def test_provider_name(self):
        from providers.mailgolem import MailgolemClient
        client = MailgolemClient()
        self.assertEqual(client.provider_name, "mailgolem")

    def test_generate_email(self):
        from providers.mailgolem import MailgolemClient
        client = MailgolemClient()
        email = client.generate_email()
        self.assertIn("@mailgolem.com", email.address)
        self.assertEqual(email.provider, "mailgolem")

    def test_list_emails(self):
        from providers.mailgolem import MailgolemClient
        client = MailgolemClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = [
            {"id": "1", "from": "a@b.com", "subject": "Test", "created_at": "2025-01-01"}
        ]
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        emails = client.list_emails("test@mailgolem.com")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Test")


class TestMuellmailClient(unittest.TestCase):
    """Muellmail.com provider test"""

    def test_provider_name(self):
        from providers.muellmail import MuellmailClient
        client = MuellmailClient()
        self.assertEqual(client.provider_name, "muellmail")

    @patch("providers.muellmail.MuellmailClient._get_domains", return_value=["muellmail.com"])
    def test_generate_email(self, *args):
        from providers.muellmail import MuellmailClient
        client = MuellmailClient()
        client._token = "test-token"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        client._session.get.return_value = mock_resp
        email = client.generate_email()
        self.assertIn("@muellmail.com", email.address)
        self.assertEqual(email.provider, "muellmail")

    def test_list_emails(self):
        from providers.muellmail import MuellmailClient
        client = MuellmailClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "data": {"emails": [
                {"id": "1", "sender": "a@b.com", "subject": "Test", "createdAt": "2025-01-01", "html": "<p>Hi</p>", "text": "Hi"}
            ]}
        }
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        emails = client.list_emails("test@muellmail.com")
        self.assertEqual(len(emails), 1)
        self.assertEqual(emails[0].subject, "Test")


class TestMailsacClient(unittest.TestCase):
    """Mailsac.com provider test"""

    def test_provider_name(self):
        from providers.mailsac import MailsacClient
        client = MailsacClient()
        self.assertEqual(client.provider_name, "mailsac")

    def test_generate_email(self):
        from providers.mailsac import MailsacClient
        client = MailsacClient()
        email = client.generate_email()
        self.assertIn("@mailsac.com", email.address)
        self.assertEqual(email.provider, "mailsac")


class TestTempmailGuruClient(unittest.TestCase):
    """Tempmail.guru provider test"""

    def test_provider_name(self):
        from providers.tempmail_guru import TempmailGuruClient
        client = TempmailGuruClient()
        self.assertEqual(client.provider_name, "tempmail.guru")

    @patch("providers.tempmail_guru.TempmailGuruClient._get_domains", return_value=["tempmail.guru"])
    def test_generate_email(self, *args):
        from providers.tempmail_guru import TempmailGuruClient
        client = TempmailGuruClient()
        client._token = "test-token"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        email = client.generate_email()
        self.assertIn("@tempmail.guru", email.address)
        self.assertEqual(email.provider, "tempmail.guru")


class TestCrazymailingClient(unittest.TestCase):
    """Crazymailing.com provider test"""

    def test_provider_name(self):
        from providers.crazymailing import CrazymailingClient
        client = CrazymailingClient()
        self.assertEqual(client.provider_name, "crazymailing")

    @patch("providers.crazymailing.CrazymailingClient._get_domains", return_value=["crazymailing.com"])
    def test_generate_email(self, *args):
        from providers.crazymailing import CrazymailingClient
        client = CrazymailingClient()
        client._token = "test-token"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        email = client.generate_email()
        self.assertIn("@crazymailing.com", email.address)
        self.assertEqual(email.provider, "crazymailing")


class TestEyepasteClient(unittest.TestCase):
    """Eyepaste.com provider test"""

    def test_provider_name(self):
        from providers.eyepaste import EyepasteClient
        client = EyepasteClient()
        self.assertEqual(client.provider_name, "eyepaste")

    def test_generate_email(self):
        from providers.eyepaste import EyepasteClient
        client = EyepasteClient()
        email = client.generate_email()
        self.assertIn("@eyepaste.com", email.address)
        self.assertEqual(email.provider, "eyepaste")

    def test_list_emails_empty(self):
        from providers.eyepaste import EyepasteClient
        client = EyepasteClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<?xml version="1.0"?><rss><channel><title>inbox</title></channel></rss>'
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        emails = client.list_emails("test@eyepaste.com")
        self.assertEqual(len(emails), 0)


class TestSegamailClient(unittest.TestCase):
    """Segamail.com provider test"""

    def test_provider_name(self):
        from providers.segamail import SegamailClient
        client = SegamailClient()
        self.assertEqual(client.provider_name, "segamail")

    def test_generate_email(self):
        from providers.segamail import SegamailClient
        client = SegamailClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"address": "test@segamail.com", "recover_key": "key123"}
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        email = client.generate_email()
        self.assertEqual(email.address, "test@segamail.com")
        self.assertEqual(email.provider, "segamail")


class TestTempmailsNetClient(unittest.TestCase):
    """Tempmails.net provider test"""

    def test_provider_name(self):
        from providers.tempmails_net import TempmailsNetClient
        client = TempmailsNetClient()
        self.assertEqual(client.provider_name, "tempmails.net")


class TestTempmailsoClient(unittest.TestCase):
    """Tempmailso.com provider test"""

    def test_provider_name(self):
        from providers.tempmailso import TempmailsoClient
        client = TempmailsoClient()
        self.assertEqual(client.provider_name, "tempmailso")

    @patch("providers.tempmailso.TempmailsoClient._get_domains", return_value=["tempmailso.com"])
    def test_generate_email(self, *args):
        from providers.tempmailso import TempmailsoClient
        client = TempmailsoClient()
        client._token = "test-token"
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        email = client.generate_email()
        self.assertIn("@tempmailso.com", email.address)
        self.assertEqual(email.provider, "tempmailso")


class TestHaribuClient(unittest.TestCase):
    """Haribu.net provider test"""

    def test_provider_name(self):
        from providers.haribu import HaribuClient
        client = HaribuClient()
        self.assertEqual(client.provider_name, "haribu")

    def test_generate_email(self):
        from providers.haribu import HaribuClient
        client = HaribuClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.text = '<html><body><input id="eposta_adres" value="test@yevme.com"></body></html>'
        client._session = MagicMock()
        client._session.get.return_value = mock_resp
        email = client.generate_email()
        self.assertEqual(email.address, "test@yevme.com")
        self.assertEqual(email.provider, "haribu")


class TestIncognitomailClient(unittest.TestCase):
    """Incognitomail.co provider test"""

    def test_provider_name(self):
        from providers.incognitomail import IncognitomailClient
        client = IncognitomailClient()
        self.assertEqual(client.provider_name, "incognitomail")

    def test_generate_email(self):
        from providers.incognitomail import IncognitomailClient
        client = IncognitomailClient()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"id": "test@mailfast.pro", "token": "test-token"}
        client._session = MagicMock()
        client._session.post.return_value = mock_resp
        email = client.generate_email()
        self.assertEqual(email.address, "test@mailfast.pro")
        self.assertEqual(email.provider, "incognitomail")


class TestTempmailEmailMock(unittest.TestCase):
    """Tempmail.email uses Mail.tm API (same as MailTmClient)"""

    def test_class_inheritance(self):
        from providers.tempmail_email import TempmailEmailClient
        from providers.mail_tm import MailTmClient
        self.assertTrue(issubclass(TempmailEmailClient, MailTmClient))

    def test_provider_name(self):
        from providers.tempmail_email import TempmailEmailClient
        client = TempmailEmailClient()
        self.assertEqual(client.provider_name, 'tempmail.email')


class TestInternxtMock(unittest.TestCase):
    """Internxt uses Mail.tm API (same as MailTmClient)"""

    def test_class_inheritance(self):
        from providers.internxt import InternxtClient
        from providers.mail_tm import MailTmClient
        self.assertTrue(issubclass(InternxtClient, MailTmClient))

    def test_provider_name(self):
        from providers.internxt import InternxtClient
        client = InternxtClient()
        self.assertEqual(client.provider_name, 'internxt')


class TestLroidMock(unittest.TestCase):
    """Lroid uses Tempail pattern"""

    def test_class_exists(self):
        from providers.lroid import LroidClient
        self.assertTrue(callable(LroidClient))

    def test_provider_name(self):
        from providers.lroid import LroidClient
        client = LroidClient()
        self.assertEqual(client.provider_name, 'lroid')


class TestMailTempMock(unittest.TestCase):
    """Mail-temp.com uses Generatoremail pattern"""

    def test_class_inheritance(self):
        from providers.mail_temp import MailTempClient
        from providers.generator_email import GeneratorEmailClient
        self.assertTrue(issubclass(MailTempClient, GeneratorEmailClient))

    def test_provider_name(self):
        from providers.mail_temp import MailTempClient
        client = MailTempClient()
        self.assertEqual(client.provider_name, 'mail-temp')


class TestMailcatchMock(unittest.TestCase):
    """MailCatch.com provider test"""

    def test_class_exists(self):
        from providers.mailcatch import MailcatchClient
        self.assertTrue(callable(MailcatchClient))

    def test_provider_name(self):
        from providers.mailcatch import MailcatchClient
        client = MailcatchClient()
        self.assertEqual(client.provider_name, 'mailcatch')

    def test_generate_email(self):
        from providers.mailcatch import MailcatchClient
        client = MailcatchClient()
        email = client.generate_email()
        self.assertTrue(email.address.endswith('@mailcatch.com'))
        self.assertEqual(email.provider, 'mailcatch')


class TestSharklasersMock(unittest.TestCase):
    """SharkLasers is a GuerrillaMail alias"""

    def test_class_inheritance(self):
        from providers.sharklasers import SharklasersClient
        from providers.guerrillamail import GuerrillaMailClient
        self.assertTrue(issubclass(SharklasersClient, GuerrillaMailClient))

    def test_provider_name(self):
        from providers.sharklasers import SharklasersClient
        client = SharklasersClient()
        self.assertEqual(client.provider_name, 'sharklasers')
