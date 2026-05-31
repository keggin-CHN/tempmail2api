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
