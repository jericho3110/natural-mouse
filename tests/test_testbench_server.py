import http.client
import json
import unittest

from testbench.server import MAX_BODY_BYTES, BenchServer, validate_batch


class TestValidateBatch(unittest.TestCase):
    def test_accepts_known_events(self):
        batch = validate_batch(b'[{"type": "wheel", "t": 1.5, "deltaY": 100}]')
        self.assertEqual(batch[0]["deltaY"], 100)

    def test_rejects_everything_else(self):
        for raw in (b'{"type": "wheel"}', b'[{"type": "eval", "t": 1}]', b'[{"type": "wheel"}]', b"[1]", b"nope"):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                validate_batch(raw)


class TestBenchServer(unittest.TestCase):
    def setUp(self):
        self.server = BenchServer("<p>page</p>", token="secret-token")
        self.server.start()
        self.addCleanup(self.server.stop)

    def request(self, method, path, body=None, host=None):
        conn = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=5)
        headers = {"Host": host or f"127.0.0.1:{self.server.port}"}
        if body is not None:
            headers["Content-Type"] = "application/json"
        conn.request(method, path, body=body, headers=headers)
        response = conn.getresponse()
        data = response.read()
        conn.close()
        return response.status, data, response

    def test_listens_on_loopback_only(self):
        self.assertEqual(self.server._httpd.server_address[0], "127.0.0.1")

    def test_serves_page_with_token(self):
        status, data, response = self.request("GET", "/?t=secret-token")
        self.assertEqual(status, 200)
        self.assertEqual(data, b"<p>page</p>")
        self.assertIn("default-src 'none'", response.getheader("Content-Security-Policy"))

    def test_refuses_without_token_or_with_wrong_host(self):
        self.assertEqual(self.request("GET", "/")[0], 404)
        self.assertEqual(self.request("GET", "/?t=wrong")[0], 404)
        # DNS rebinding: right token, but the browser thinks it's another site.
        self.assertEqual(self.request("GET", "/?t=secret-token", host="evil.example:80")[0], 404)

    def test_collects_posted_events(self):
        body = json.dumps([{"type": "ready", "t": 1}, {"type": "click", "t": 2, "target": "start"}])

        status, _, _ = self.request("POST", "/events?t=secret-token", body=body)

        self.assertEqual(status, 204)
        self.assertEqual([e["type"] for e in self.server.events()], ["ready", "click"])
        self.assertIsNotNone(self.server.wait_for(lambda e: e["type"] == "click", timeout=0.1))

    def test_rejects_bad_or_oversized_posts(self):
        self.assertEqual(self.request("POST", "/events?t=secret-token", body="not json")[0], 400)
        self.assertEqual(self.request("POST", "/events?t=wrong", body="[]")[0], 404)
        too_big = "[" + " " * MAX_BODY_BYTES + "]"
        self.assertEqual(self.request("POST", "/events?t=secret-token", body=too_big)[0], 413)
        self.assertEqual(self.server.events(), [])

    def test_wait_for_times_out(self):
        self.assertIsNone(self.server.wait_for(lambda e: True, timeout=0.05))


if __name__ == "__main__":
    unittest.main()
