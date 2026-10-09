"""A tiny local web server: serves the test page, collects its events.

The page (page.html) runs in a normal browser and POSTs batches of the
mouse/wheel/scroll/click events it saw to ``/events``. The bench reads
them back with `events()` / `wait_for()` to check what the browser
actually received, rather than trusting what we *meant* to send.

Security: it only listens on 127.0.0.1 (never the network), picks a free
port, requires a random token on every request, checks the Host header
(so a web page can't reach it through DNS rebinding), caps request size
and stored events, and only accepts JSON lists of known event types. It
never runs or evaluates anything it receives.
"""

from __future__ import annotations

import hmac
import json
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlsplit

EVENT_TYPES = frozenset({"ready", "focus", "mousemove", "wheel", "scroll", "click"})
MAX_BODY_BYTES = 256_000
MAX_EVENTS = 100_000


class BenchServer:
    """Start with `start()` (returns the page URL), stop with `stop()`.
    Also usable as a context manager: ``with BenchServer(html) as url:``."""

    def __init__(self, page_html: str, token: str | None = None):
        self._page = page_html.encode("utf-8")
        self.token = token or secrets.token_urlsafe(24)
        self._events: list[dict] = []
        self._changed = threading.Condition()
        self._httpd: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None

    # --- lifecycle -------------------------------------------------------

    def start(self) -> str:
        bench = self

        class Handler(_Handler):
            server_bench = bench

        self._httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._httpd.serve_forever, daemon=True)
        self._thread.start()
        return f"http://127.0.0.1:{self.port}/?t={self.token}"

    def stop(self) -> None:
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    def __enter__(self) -> str:
        return self.start()

    def __exit__(self, *exc) -> None:
        self.stop()

    @property
    def port(self) -> int:
        if self._httpd is None:
            raise RuntimeError("server not started")
        return self._httpd.server_address[1]

    # --- events ----------------------------------------------------------

    def add_events(self, batch: list[dict]) -> None:
        with self._changed:
            room = MAX_EVENTS - len(self._events)
            self._events.extend(batch[:max(room, 0)])
            self._changed.notify_all()

    def events(self) -> list[dict]:
        """A snapshot copy of every event received so far."""
        with self._changed:
            return list(self._events)

    def wait_for(self, predicate: Callable[[dict], bool], start: int = 0, timeout: float = 10.0) -> dict | None:
        """The first event at index >= `start` matching `predicate`, waiting
        up to `timeout` seconds for it to arrive. None on timeout."""
        deadline = time.monotonic() + timeout
        with self._changed:
            while True:
                for event in self._events[start:]:
                    if predicate(event):
                        return event
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    return None
                self._changed.wait(remaining)

    def wait_quiet(self, quiet: float = 0.6, timeout: float = 5.0) -> None:
        """Wait until no new events have arrived for `quiet` seconds (the
        page batches every 150 ms, and smooth scrolling keeps going after
        the last wheel event), or until `timeout`."""
        deadline = time.monotonic() + timeout
        with self._changed:
            seen = len(self._events)
            while time.monotonic() < deadline:
                self._changed.wait(min(quiet, max(deadline - time.monotonic(), 0)))
                if len(self._events) == seen:
                    return
                seen = len(self._events)


def validate_batch(raw: bytes) -> list[dict]:
    """Parse and check one POST body. Raises ValueError if it isn't a JSON
    list of objects with a known `type` and a numeric `t`."""
    data = json.loads(raw.decode("utf-8"))
    if not isinstance(data, list):
        raise ValueError("expected a JSON list")
    for event in data:
        if not isinstance(event, dict) or event.get("type") not in EVENT_TYPES:
            raise ValueError("unknown event")
        if not isinstance(event.get("t"), (int, float)):
            raise ValueError("event without a time")
    return data


class _Handler(BaseHTTPRequestHandler):
    server_bench: BenchServer  # set on the subclass made in start()

    def log_message(self, format, *args) -> None:  # keep the console quiet
        pass

    def _allowed(self) -> bool:
        bench = self.server_bench
        host_ok = self.headers.get("Host", "") in (f"127.0.0.1:{bench.port}", f"localhost:{bench.port}")
        token = parse_qs(urlsplit(self.path).query).get("t", [""])[0]
        return host_ok and hmac.compare_digest(token.encode(), bench.token.encode())

    def _send(self, status: int, body: bytes = b"", content_type: str = "text/plain") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if urlsplit(self.path).path != "/" or not self._allowed():
            self._send(404)
            return
        self.send_response(200)
        body = self.server_bench._page
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'",
        )
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self) -> None:
        if urlsplit(self.path).path != "/events" or not self._allowed():
            self._send(404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = -1
        if not 0 < length <= MAX_BODY_BYTES:
            self._send(413)
            return
        try:
            batch = validate_batch(self.rfile.read(length))
        except (ValueError, UnicodeDecodeError):
            self._send(400)
            return
        self.server_bench.add_events(batch)
        self._send(204)
