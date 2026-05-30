"""
单元测试
运行: python -m pytest tests/ -v
"""

import json
import time
import unittest
from unittest.mock import MagicMock, patch

from providers.base import InboxEmail, TempEmail, TempMailClient
from providers.boomlify import (
    ENCRYPTION_KEY,
    TRANSPORT_KEY_RING,
    _decrypt_response,
    _xor_decrypt,
)
from providers.utils import (
    ETagCache,
    EmailFetchError,
    EmailGenerateError,
    RateLimitError,
    TempMailError,
    retry,
)


# ───────────────────────── XOR 加解密 ─────────────────────────

class TestXorDecrypt(unittest.TestCase):

    def test_encrypt_decrypt_roundtrip(self):
        original = '{"hello": "world", "count": 42}'
        key = ENCRYPTION_KEY
        key_bytes = key.encode("utf-8")
        orig_bytes = original.encode("utf-8")
        encrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(orig_bytes))
        result = _xor_decrypt(encrypted.hex(), key)
        self.assertEqual(result, original)
        self.assertEqual(json.loads(result), {"hello": "world", "count": 42})

    def test_decrypt_response_with_encrypted_field(self):
        original = {"token": "abc123", "isGuest": True}
        key = ENCRYPTION_KEY
        key_bytes = key.encode("utf-8")
        orig_bytes = json.dumps(original).encode("utf-8")
        encrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(orig_bytes))
        data = {"encrypted": encrypted.hex()}
        result = _decrypt_response(data, key=key)
        self.assertEqual(result, original)

    def test_decrypt_response_without_encrypted_field(self):
        data = {"status": "ok", "count": 5}
        result = _decrypt_response(data)
        self.assertEqual(result, data)

    def test_decrypt_with_transport_key(self):
        key = TRANSPORT_KEY_RING["kqvtd"]
        original = '{"error": "Missing required fields"}'
        key_bytes = key.encode("utf-8")
        orig_bytes = original.encode("utf-8")
        encrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(orig_bytes))
        data = {"encrypted": encrypted.hex()}
        result = _decrypt_response(data, key_id="kqvtd")
        self.assertEqual(result, {"error": "Missing required fields"})

    def test_decrypt_response_invalid_hex(self):
        data = {"encrypted": "not_valid_hex_zzzz"}
        result = _decrypt_response(data)
        self.assertEqual(result, data)


# ───────────────────────── ETag 缓存 ─────────────────────────

class TestETagCache(unittest.TestCase):

    def test_basic_put_get(self):
        cache = ETagCache(ttl_seconds=10)
        cache.put("addr1", "etag-abc")
        self.assertEqual(cache.get("addr1"), "etag-abc")
        self.assertIsNone(cache.get("addr2"))

    def test_hit_miss_stats(self):
        cache = ETagCache(ttl_seconds=10)
        cache.put("a", "e1")
        cache.get("a")  # hit
        cache.get("a")  # hit
        cache.get("b")  # miss
        self.assertEqual(cache.hits, 2)
        self.assertEqual(cache.misses, 1)
        self.assertAlmostEqual(cache.hit_rate, 2 / 3)

    def test_ttl_expiry(self):
        cache = ETagCache(ttl_seconds=0)  # 立即过期
        cache.put("a", "e1")
        time.sleep(0.01)
        self.assertIsNone(cache.get("a"))
        self.assertEqual(cache.misses, 1)

    def test_invalidate(self):
        cache = ETagCache(ttl_seconds=60)
        cache.put("a", "e1")
        cache.invalidate("a")
        self.assertIsNone(cache.get("a"))

    def test_clear(self):
        cache = ETagCache(ttl_seconds=60)
        cache.put("a", "e1")
        cache.put("b", "e2")
        cache.clear()
        self.assertEqual(cache.hits, 0)
        self.assertIsNone(cache.get("a"))

    def test_stats_dict(self):
        cache = ETagCache(ttl_seconds=60)
        cache.put("x", "etag")
        stats = cache.stats()
        self.assertIn("hits", stats)
        self.assertIn("misses", stats)
        self.assertIn("hit_rate", stats)
        self.assertIn("cached_keys", stats)
        self.assertEqual(stats["cached_keys"], 1)


# ───────────────────────── 异常类 ─────────────────────────

class TestExceptions(unittest.TestCase):

    def test_hierarchy(self):
        self.assertTrue(issubclass(EmailGenerateError, TempMailError))
        self.assertTrue(issubclass(EmailFetchError, TempMailError))
        self.assertTrue(issubclass(RateLimitError, TempMailError))
        self.assertTrue(issubclass(TempMailError, Exception))

    def test_rate_limit_retry_after(self):
        e = RateLimitError(retry_after=30.0)
        self.assertEqual(e.retry_after, 30.0)
        self.assertIn("30", str(e))


# ───────────────────────── 重试 ─────────────────────────

class TestRetry(unittest.TestCase):

    def test_success_on_first_try(self):
        call_count = 0
        @retry(max_attempts=3, backoff_factor=0.01)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"
        self.assertEqual(succeed(), "ok")
        self.assertEqual(call_count, 1)

    def test_success_after_retries(self):
        call_count = 0
        @retry(max_attempts=3, backoff_factor=0.01, exceptions=(ValueError,))
        def fail_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ValueError("not yet")
            return "done"
        self.assertEqual(fail_twice(), "done")
        self.assertEqual(call_count, 3)

    def test_exhausted_retries(self):
        @retry(max_attempts=2, backoff_factor=0.01, exceptions=(ValueError,))
        def always_fail():
            raise ValueError("always")
        with self.assertRaises(ValueError):
            always_fail()

    def test_non_retryable_exception(self):
        call_count = 0
        @retry(max_attempts=3, backoff_factor=0.01, exceptions=(ValueError,))
        def type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")
        with self.assertRaises(TypeError):
            type_error()
        self.assertEqual(call_count, 1)


# ───────────────────────── 数据模型 ─────────────────────────

class TestBaseModels(unittest.TestCase):

    def test_temp_email_defaults(self):
        email = TempEmail(address="test@example.com", provider="test")
        self.assertEqual(email.address, "test@example.com")
        self.assertIsNone(email.expires_at)
        self.assertEqual(email.raw, {})

    def test_inbox_email_defaults(self):
        email = InboxEmail(id="123", provider="test")
        self.assertEqual(email.id, "123")
        self.assertIsNone(email.subject)
        self.assertEqual(email.raw, {})


if __name__ == "__main__":
    unittest.main()
