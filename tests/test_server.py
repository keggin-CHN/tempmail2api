"""
API 服务集成测试 — 4 个经实测验证的 provider
运行: python -m pytest tests/test_server.py -v
"""

import json
import threading
import time
import unittest
from http.client import HTTPConnection

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import APIHandler, HTTPServer


class TestAPIServer(unittest.TestCase):
    """API 服务集成测试"""

    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), APIHandler)
        cls.port = cls.server.server_address[1]
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        time.sleep(0.5)

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()

    def _get(self, path):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = json.loads(resp.read().decode())
        conn.close()
        return resp.status, body

    def _post(self, path, data=None):
        conn = HTTPConnection("127.0.0.1", self.port, timeout=10)
        headers = {"Content-Type": "application/json"}
        body_str = json.dumps(data) if data else ""
        conn.request("POST", path, body=body_str, headers=headers)
        resp = conn.getresponse()
        body = json.loads(resp.read().decode())
        conn.close()
        return resp.status, body

    def test_root_endpoint(self):
        status, body = self._get("/")
        self.assertEqual(status, 200)
        self.assertIn("service", body)
        self.assertEqual(body["service"], "chatgptmail-2api")

    def test_providers_endpoint(self):
        status, body = self._get("/api/providers")
        self.assertEqual(status, 200)
        self.assertIn("inboxkitten", body["providers"])
        self.assertIn("mailnesia", body["providers"])
        self.assertIn("anonymmail", body["providers"])
        self.assertIn("tempmaillol", body["providers"])
        self.assertIn("chatgptmail", body["providers"])
        self.assertIn("tempmail", body["providers"])
        self.assertIn("emailtick", body["providers"])
        self.assertIn("verified", body)

    def test_generate_unknown_provider(self):
        status, body = self._post("/api/generate", {"provider": "nonexistent"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_inbox_missing_address(self):
        status, body = self._get("/api/inbox")
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_not_found(self):
        status, body = self._get("/api/nonexistent")
        self.assertEqual(status, 404)

    def test_health_endpoint(self):
        status, body = self._get("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body["status"], "ok")
        self.assertIn("uptime_seconds", body)
        self.assertIn("providers", body)
        self.assertIsInstance(body["providers"], list)
        self.assertEqual(len(body["providers"]), 10)  # 7 个 provider + 3 个别名

    def test_openapi_docs_endpoint(self):
        status, body = self._get("/api/docs")
        self.assertEqual(status, 200)
        self.assertEqual(body["openapi"], "3.0.3")
        self.assertIn("info", body)
        self.assertIn("paths", body)
        self.assertIn("/api/health", body["paths"])
        self.assertIn("/api/generate", body["paths"])
        self.assertIn("/api/inbox", body["paths"])

    def test_cors_preflight(self):
        import http.client
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        conn.request("OPTIONS", "/api/generate")
        resp = conn.getresponse()
        self.assertEqual(resp.status, 204)
        self.assertIn("*", resp.getheader("Access-Control-Allow-Origin"))
        conn.close()


if __name__ == "__main__":
    unittest.main()
