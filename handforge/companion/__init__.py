"""Opt-in remote queue monitoring and shared-workstation control (LAN web UI).

Privacy: off by default. Binds to localhost unless explicitly opened to the
LAN with a shared token. Status is derived from live Orchestrator state.
Mutating control endpoints always require ``companion_token``.
"""

from .control import SessionController
from .server import CompanionServer, companion_url, resolve_companion_bind
from .status import QueueStatusHub, serialize_job_summary, serialize_status

__all__ = [
    "CompanionServer",
    "QueueStatusHub",
    "SessionController",
    "companion_url",
    "resolve_companion_bind",
    "serialize_job_summary",
    "serialize_status",
]
