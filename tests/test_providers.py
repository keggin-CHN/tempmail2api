"""
单元测试
运行: python -m pytest tests/ -v
"""

import json
import unittest
from unittest.mock import MagicMock, patch

from providers.base import InboxEmail, TempEmail, TempMailClient
from providers.boomlify import (
    ENCRYPTION_KEY,
    TRANSPORT_KEY_RING,
    _decrypt_response,
    _xor_decrypt,
)
from providers.utils import retry


class TestXorDecrypt(unittest.TestCase):
    """测试 XOR 加密解密"""

    def test_encrypt_decrypt_roundtrip(self):
        """加密后再解密应得到原文"""
        original = '{"hello": "world", "count": 42}'
        key = ENCRYPTION_KEY

        # 加密
        key_bytes = key.encode("utf-8")
        orig_bytes = original.encode("utf-8")
        encrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(orig_bytes))
        encrypted_hex = encrypted.hex()

        # 解密
        result = _xor_decrypt(encrypted_hex, key)
        self.assertEqual(result, original)
        self.assertEqual(json.loads(result), {"hello": "world", "count": 42})

    def test_decrypt_response_with_encrypted_field(self):
        """_decrypt_response 应正确解密包含 encrypted 字段的响应"""
        original = {"token": "abc123", "isGuest": True}
        key = ENCRYPTION_KEY

        key_bytes = key.encode("utf-8")
        orig_bytes = json.dumps(original).encode("utf-8")
        encrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(orig_bytes))

        data = {"encrypted": encrypted.hex()}
        result = _decrypt_response(data, key=key)
        self.assertEqual(result, original)

    def test_decrypt_response_without_encrypted_field(self):
        """不包含 encrypted 字段的响应应原样返回"""
        data = {"status": "ok", "count": 5}
        result = _decrypt_response(data)
        self.assertEqual(result, data)

    def test_decrypt_with_transport_key(self):
        """使用 transport key ring 中的密钥解密"""
        # 使用 kqvtd 对应的密钥加密
        key = TRANSPORT_KEY_RING["kqvtd"]
        original = '{"error": "Missing required fields"}'

        key_bytes = key.encode("utf-8")
        orig_bytes = original.encode("utf-8")
        encrypted = bytes(b ^ key_bytes[i % len(key_bytes)] for i, b in enumerate(orig_bytes))

        data = {"encrypted": encrypted.hex()}
        result = _decrypt_response(data, key_id="kqvtd")
        self.assertEqual(result, {"error": "Missing required fields"})

    def test_decrypt_response_invalid_hex(self):
        """无效的 hex 数据应原样返回"""
        data = {"encrypted": "not_valid_hex_zzzz"}
        result = _decrypt_response(data)
        # 异常时返回原始数据
        self.assertEqual(result, data)


class TestRetry(unittest.TestCase):
    """测试重试装饰器"""

    def test_success_on_first_try(self):
        call_count = 0

        @retry(max_attempts=3, backoff_factor=0.01)
        def succeed():
            nonlocal call_count
            call_count += 1
            return "ok"

        result = succeed()
        self.assertEqual(result, "ok")
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

        result = fail_twice()
        self.assertEqual(result, "done")
        self.assertEqual(call_count, 3)

    def test_exhausted_retries(self):
        @retry(max_attempts=2, backoff_factor=0.01, exceptions=(ValueError,))
        def always_fail():
            raise ValueError("always")

        with self.assertRaises(ValueError):
            always_fail()

    def test_non_retryable_exception(self):
        """不在 retryable 列表中的异常不应重试"""
        call_count = 0

        @retry(max_attempts=3, backoff_factor=0.01, exceptions=(ValueError,))
        def type_error():
            nonlocal call_count
            call_count += 1
            raise TypeError("wrong type")

        with self.assertRaises(TypeError):
            type_error()
        self.assertEqual(call_count, 1)


class TestBaseModels(unittest.TestCase):
    """测试数据模型"""

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
