"""Opt-in remote queue monitoring (companion web / LAN phone browser).

Privacy: off by default. Binds to localhost unless explicitly opened to the
LAN with a shared token. Status is derived from live Orchestrator state.
"""

from .server import CompanionServer, companion_url, resolve_companion_bind
from .status import QueueStatusHub, serialize_job_summary, serialize_status

__all__ = [
    "CompanionServer",
    "QueueStatusHub",
    "companion_url",
    "resolve_companion_bind",
    "serialize_job_summary",
    "serialize_status",
]
