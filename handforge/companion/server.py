"""Local HTTP companion server for remote queue monitoring and shared control.

Default-safe: opt-in, localhost bind, shared token required for LAN binds.
Mutating control endpoints always require a configured shared token (even on
localhost). Uses stdlib only (no extra deps). Clients poll ``GET /api/status``.
"""

from __future__ import annotations

import json
import secrets
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, Optional, Tuple
from urllib.parse import parse_qs, urlparse

from .control import SessionController
from .status import QueueStatusHub

SETTING_ENABLED = "companion_enabled"
SETTING_HOST = "companion_host"
SETTING_PORT = "companion_port"
SETTING_TOKEN = "companion_token"

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8765
STATIC_DIR = Path(__file__).resolve().parent / "static"


def is_loopback_host(host: str) -> bool:
    h = (host or "").strip().lower()
    return h in {"127.0.0.1", "localhost", "::1", ""}


def generate_token() -> str:
    return secrets.token_urlsafe(24)


def resolve_companion_bind(
    settings: Optional[Dict[str, Any]] = None,
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    token: Optional[str] = None,
    lan: bool = False,
) -> Tuple[str, int, str]:
    """Resolve host/port/token with safety rules.

    - Default host is localhost.
    - ``lan=True`` switches host to ``0.0.0.0``.
    - Non-loopback binds require a non-empty token (auto-generated if missing).
    """
    cfg = dict(settings or {})
    bind_host = (host if host is not None else cfg.get(SETTING_HOST) or DEFAULT_HOST).strip()
    if lan:
        bind_host = "0.0.0.0"
    try:
        bind_port = int(port if port is not None else cfg.get(SETTING_PORT) or DEFAULT_PORT)
    except (TypeError, ValueError):
        bind_port = DEFAULT_PORT
    bind_port = max(1, min(65535, bind_port))

    bind_token = token if token is not None else str(cfg.get(SETTING_TOKEN) or "")
    bind_token = bind_token.strip()
    if not is_loopback_host(bind_host) and not bind_token:
        bind_token = generate_token()
    return bind_host, bind_port, bind_token


def companion_enabled(settings: Optional[Dict[str, Any]] = None) -> bool:
    if not settings:
        return False
    return bool(settings.get(SETTING_ENABLED, False))


def companion_url(host: str, port: int, token: str = "", *, prefer_lan_hint: bool = True) -> str:
    """Build a browser URL. For ``0.0.0.0``, substitute a LAN IP hint when possible."""
    display = host
    if host in {"0.0.0.0", "::"}:
        display = _guess_lan_ip() if prefer_lan_hint else "127.0.0.1"
    base = f"http://{display}:{int(port)}/"
    if token:
        return f"{base}?token={token}"
    return base


def _guess_lan_ip() -> str:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"


def format_companion_status(settings: Optional[Dict[str, Any]] = None) -> str:
    cfg = dict(settings or {})
    enabled = companion_enabled(cfg)
    host, port, token = resolve_companion_bind(cfg)
    lines = [
        "Companion remote queue monitor / shared workstation UI:",
        f"  enabled: {'yes' if enabled else 'no (opt-in; default off)'}",
        f"  bind: {host}:{port}",
        f"  token: {'set' if token else 'none (ok for localhost status; required for control writes)'}",
    ]
    if not is_loopback_host(host):
        lines.append(
            "  warning: LAN bind exposes queue filenames and (with token) start/stop/"
            "enqueue control to anyone with the token on your network. "
            "Prefer localhost or a firewall."
        )
    else:
        lines.append(
            "  note: mutating /api/control/* always requires companion_token, "
            "even on localhost."
        )
    if enabled:
        lines.append(f"  open on phone / shared UI: {companion_url(host, port, token)}")
    return "\n".join(lines)


class CompanionServer:
    """Background ThreadingHTTPServer exposing status JSON + shared workstation UI."""

    def __init__(
        self,
        hub: QueueStatusHub,
        *,
        host: str = DEFAULT_HOST,
        port: int = DEFAULT_PORT,
        token: str = "",
        controller: Optional[SessionController] = None,
    ) -> None:
        if not is_loopback_host(host) and not (token or "").strip():
            raise ValueError(
                "Companion LAN bind requires a shared token "
                "(set companion_token or pass --token)"
            )
        self.hub = hub
        self.controller = controller
        self.host = host
        self.port = int(port)
        self.token = (token or "").strip()
        self._httpd: Optional[ThreadingHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._started = False

    @property
    def url(self) -> str:
        return companion_url(self.host, self.port, self.token)

    @property
    def running(self) -> bool:
        return bool(self._started and self._httpd is not None)

    def start(self) -> "CompanionServer":
        if self._started:
            return self
        hub = self.hub
        controller = self.controller
        expected_token = self.token

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, fmt: str, *args: Any) -> None:  # noqa: A003
                return  # quiet by default

            def _unauthorized(self, *, reason: str = "unauthorized") -> None:
                body = json.dumps({"error": reason}).encode("utf-8")
                self.send_response(401)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _forbidden_writes(self) -> None:
                body = json.dumps(
                    {
                        "error": "write_token_required",
                        "message": (
                            "Set companion_token (Preferences or --token) to enable "
                            "shared workstation control writes."
                        ),
                    }
                ).encode("utf-8")
                self.send_response(403)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _check_auth(self) -> bool:
                if not expected_token:
                    return True
                auth = self.headers.get("Authorization") or ""
                if auth.lower().startswith("bearer ") and auth[7:].strip() == expected_token:
                    return True
                header_token = self.headers.get("X-HandForge-Token") or ""
                if header_token.strip() == expected_token:
                    return True
                qs = parse_qs(urlparse(self.path).query)
                if (qs.get("token") or [""])[0] == expected_token:
                    return True
                return False

            def _check_write_auth(self) -> str:
                """Return '' if OK, else an error token: 'no_token' | 'unauthorized'."""
                if not expected_token:
                    return "no_token"
                if not self._check_auth():
                    return "unauthorized"
                return ""

            def _send_bytes(
                self,
                data: bytes,
                *,
                content_type: str,
                status: int = 200,
            ) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.end_headers()
                self.wfile.write(data)

            def _send_json(self, payload: Any, *, status: int = 200) -> None:
                data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self._send_bytes(
                    data, content_type="application/json; charset=utf-8", status=status
                )

            def _read_json_body(self) -> Dict[str, Any]:
                length = int(self.headers.get("Content-Length") or 0)
                if length <= 0:
                    return {}
                if length > 1_000_000:
                    raise ValueError("body_too_large")
                raw = self.rfile.read(length)
                if not raw:
                    return {}
                data = json.loads(raw.decode("utf-8"))
                if not isinstance(data, dict):
                    raise ValueError("body_must_be_object")
                return data

            def do_GET(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                path = parsed.path or "/"

                if path == "/api/health":
                    # Health is unauthenticated so operators can probe bind without leaking jobs.
                    payload = {
                        "ok": True,
                        "auth_required": bool(expected_token),
                        "control": controller is not None,
                        "writes_require_token": True,
                    }
                    self._send_json(payload)
                    return

                if path in {"/api/status", "/api/status/"}:
                    if not self._check_auth():
                        self._unauthorized()
                        return
                    snap = hub.snapshot()
                    snap["control_available"] = controller is not None
                    self._send_json(snap)
                    return

                if path in {"/api/control", "/api/control/"}:
                    if not self._check_auth():
                        self._unauthorized()
                        return
                    if controller is None:
                        self._send_json(
                            {"control": False, "error": "control_unavailable"},
                            status=404,
                        )
                        return
                    self._send_json(controller.control_snapshot())
                    return

                if path in {"/", "/index.html"}:
                    if not self._check_auth():
                        self._unauthorized()
                        return
                    index = STATIC_DIR / "index.html"
                    if not index.is_file():
                        self._send_bytes(
                            b"Companion UI missing",
                            content_type="text/plain; charset=utf-8",
                            status=500,
                        )
                        return
                    data = index.read_bytes()
                    self._send_bytes(data, content_type="text/html; charset=utf-8")
                    return

                if path.startswith("/static/"):
                    if not self._check_auth():
                        self._unauthorized()
                        return
                    rel = path[len("/static/") :]
                    target = (STATIC_DIR / rel).resolve()
                    if not str(target).startswith(str(STATIC_DIR.resolve())) or not target.is_file():
                        self._send_bytes(b"Not found", content_type="text/plain", status=404)
                        return
                    ctype = "application/octet-stream"
                    if target.suffix == ".css":
                        ctype = "text/css; charset=utf-8"
                    elif target.suffix == ".js":
                        ctype = "application/javascript; charset=utf-8"
                    self._send_bytes(target.read_bytes(), content_type=ctype)
                    return

                self._send_bytes(b"Not found", content_type="text/plain", status=404)

            def do_POST(self) -> None:  # noqa: N802
                parsed = urlparse(self.path)
                path = (parsed.path or "/").rstrip("/") or "/"

                write_err = self._check_write_auth()
                if write_err == "no_token":
                    self._forbidden_writes()
                    return
                if write_err == "unauthorized":
                    self._unauthorized()
                    return

                if controller is None:
                    self._send_json(
                        {"ok": False, "error": "control_unavailable"},
                        status=404,
                    )
                    return

                try:
                    body = self._read_json_body()
                except Exception as exc:  # noqa: BLE001
                    self._send_json(
                        {"ok": False, "error": "invalid_json", "detail": str(exc)},
                        status=400,
                    )
                    return

                try:
                    if path == "/api/control/start":
                        self._send_json(controller.start())
                        return
                    if path == "/api/control/stop":
                        self._send_json(controller.stop())
                        return
                    if path == "/api/control/jobs":
                        paths = body.get("paths") or body.get("files") or []
                        if not isinstance(paths, list):
                            self._send_json(
                                {"ok": False, "error": "paths_must_be_list"},
                                status=400,
                            )
                            return
                        self._send_json(controller.add_paths([str(p) for p in paths]))
                        return
                    if path == "/api/control/jobs/remove":
                        scope = str(body.get("scope") or "pending").strip().lower()
                        try:
                            index = int(body.get("index"))
                        except (TypeError, ValueError):
                            self._send_json(
                                {"ok": False, "error": "index_required"},
                                status=400,
                            )
                            return
                        if scope == "queued":
                            self._send_json(controller.remove_queued(index))
                        else:
                            self._send_json(controller.remove_pending(index))
                        return
                    if path == "/api/control/jobs/clear":
                        self._send_json(controller.clear_pending())
                        return
                    if path == "/api/control/options":
                        self._send_json(
                            controller.set_options(
                                output_dir=body.get("output_dir"),
                                preset=body.get("preset"),
                                format=body.get("format"),
                                mode=body.get("mode"),
                                bitrate=body.get("bitrate"),
                            )
                        )
                        return
                except Exception as exc:  # noqa: BLE001 — never crash the server thread
                    self._send_json(
                        {"ok": False, "error": "control_failed", "detail": str(exc)},
                        status=500,
                    )
                    return

                self._send_json({"ok": False, "error": "not_found"}, status=404)

        httpd = ThreadingHTTPServer((self.host, self.port), Handler)
        httpd.daemon_threads = True
        self._httpd = httpd
        thread = threading.Thread(target=httpd.serve_forever, name="handforge-companion", daemon=True)
        self._thread = thread
        thread.start()
        self._started = True
        return self

    def stop(self) -> None:
        httpd = self._httpd
        self._httpd = None
        self._started = False
        if httpd is not None:
            try:
                httpd.shutdown()
            except Exception:  # noqa: BLE001
                pass
            try:
                httpd.server_close()
            except Exception:  # noqa: BLE001
                pass
        self._thread = None


def start_companion_from_settings(
    hub: QueueStatusHub,
    settings: Dict[str, Any],
    *,
    host: Optional[str] = None,
    port: Optional[int] = None,
    token: Optional[str] = None,
    lan: bool = False,
    force: bool = False,
    controller: Optional[SessionController] = None,
) -> Optional[CompanionServer]:
    """Start companion if enabled (or ``force``). Returns None when disabled."""
    if not force and not companion_enabled(settings):
        return None
    bind_host, bind_port, bind_token = resolve_companion_bind(
        settings, host=host, port=port, token=token, lan=lan
    )
    server = CompanionServer(
        hub,
        host=bind_host,
        port=bind_port,
        token=bind_token,
        controller=controller,
    )
    server.start()
    return server
