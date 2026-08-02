"""Outbound-only private data-plane heartbeat utility.

It deliberately has no source-data upload or job-claim path. A private worker
may retain raw series and credentials in its own environment and return only a
signed, derived-finding manifest after a separate signed-job protocol is
implemented and reviewed.
"""

from __future__ import annotations

import argparse
import json
import ssl
import time
from datetime import UTC, datetime
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .config import Settings, get_settings


def status(settings: Settings) -> dict[str, Any]:
    configured = bool(settings.control_plane_heartbeat_url)
    return {
        "status": "configured" if configured else "not_configured",
        "data_plane_id": settings.data_plane_id if configured else None,
        "transport": "outbound_mtls_https" if configured else None,
        "raw_data_transfer": False,
        "message": (
            "Heartbeat configuration is present; invoke with --heartbeat to send metadata only."
            if configured
            else "No control-plane heartbeat is configured; no network request was made."
        ),
    }


def send_heartbeat(settings: Settings) -> dict[str, Any]:
    """Send only metadata, returning a structured health result on any failure."""

    current = status(settings)
    if current["status"] != "configured":
        return current
    assert settings.control_plane_heartbeat_url is not None
    assert settings.data_plane_id is not None
    assert settings.data_plane_client_cert is not None
    assert settings.data_plane_client_key is not None

    try:
        context = ssl.create_default_context()
        context.load_cert_chain(settings.data_plane_client_cert, settings.data_plane_client_key)
        body = json.dumps(
            {
                "data_plane_id": settings.data_plane_id,
                "sent_at": datetime.now(UTC).isoformat(),
                "raw_data_transfer": False,
            }
        ).encode("utf-8")
        request = Request(
            settings.control_plane_heartbeat_url,
            data=body,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=10, context=context) as response:
            current["status"] = "healthy" if 200 <= response.status < 300 else "degraded"
            current["http_status"] = response.status
    except HTTPError as exc:
        current["status"] = "degraded"
        current["http_status"] = exc.code
    except (URLError, OSError, ssl.SSLError, ValueError) as exc:
        current["status"] = "unreachable"
        current["reason"] = type(exc).__name__
    return current


def _positive_seconds(value: str) -> int:
    try:
        seconds = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("interval must be a positive integer") from exc
    if seconds < 1:
        raise argparse.ArgumentTypeError("interval must be at least one second")
    return seconds


def _emit(result: dict[str, Any]) -> None:
    print(json.dumps(result, sort_keys=True), flush=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="NimbusX private data-plane status utility")
    parser.add_argument(
        "--heartbeat", action="store_true", help="send a metadata-only mTLS heartbeat"
    )
    parser.add_argument(
        "--loop", action="store_true", help="repeat a heartbeat until the process is stopped"
    )
    parser.add_argument(
        "--interval-seconds",
        type=_positive_seconds,
        default=30,
        help="heartbeat interval when --loop is used (default: 30)",
    )
    args = parser.parse_args()
    if args.loop and not args.heartbeat:
        parser.error("--loop requires --heartbeat")

    settings = get_settings()
    if not args.loop:
        result = send_heartbeat(settings) if args.heartbeat else status(settings)
        _emit(result)
        return 0 if result["status"] in {"configured", "not_configured", "healthy"} else 1

    while True:
        result = send_heartbeat(settings)
        _emit(result)
        if result["status"] == "not_configured":
            return 2
        time.sleep(args.interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
