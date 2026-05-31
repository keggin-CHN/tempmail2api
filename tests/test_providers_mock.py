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
