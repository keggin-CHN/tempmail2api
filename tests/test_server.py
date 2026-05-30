"""
API 服务集成测试
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
        self.assertIn("tempmail", body["providers"])
        self.assertIn("boomlify", body["providers"])
        self.assertIn("chatgptmail", body["providers"])

    def test_generate_tempmail(self):
        status, body = self._post("/api/generate", {"provider": "tempmail", "duration": 10})
        self.assertEqual(status, 200)
        self.assertIn("@", body["address"])
        self.assertEqual(body["provider"], "tempmail.ing")

    def test_generate_boomlify(self):
        status, body = self._post("/api/generate", {"provider": "boomlify"})
        self.assertEqual(status, 200)
        self.assertIn("@", body["address"])
        self.assertEqual(body["provider"], "boomlify")

    def test_generate_unknown_provider(self):
        status, body = self._post("/api/generate", {"provider": "nonexistent"})
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_inbox_missing_address(self):
        status, body = self._get("/api/inbox")
        self.assertEqual(status, 400)
        self.assertIn("error", body)

    def test_domains_boomlify(self):
        status, body = self._get("/api/domains?provider=boomlify")
        self.assertEqual(status, 200)
        self.assertGreater(body["count"], 0)
        self.assertTrue(all("domain" in d for d in body["domains"]))

    def test_not_found(self):
        status, body = self._get("/api/nonexistent")
        self.assertEqual(status, 404)


if __name__ == "__main__":
    unittest.main()
