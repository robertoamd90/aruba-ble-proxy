from __future__ import annotations

import argparse
import asyncio
import logging
import os

from .server import ArubaBleReceiver, SummaryEventLogger


def main() -> None:
    args = parse_args()
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    logging.getLogger("websockets").setLevel(logging.INFO)
    if args.summary:
        logging.getLogger("custom_components.aruba_ble_proxy.aruba_proto").setLevel(logging.WARNING)

    receiver = ArubaBleReceiver(
        host=args.host,
        port=args.port,
        access_token=args.access_token,
        event_handler=SummaryEventLogger() if args.summary else None,
    )
    try:
        asyncio.run(receiver.run())
    except KeyboardInterrupt:
        logging.getLogger(__name__).info("Aruba BLE receiver stopped")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the standalone Aruba BLE receiver")
    parser.add_argument("--host", default=os.environ.get("ARUBA_BLE_PROXY_HOST", "0.0.0.0"))
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("ARUBA_BLE_PROXY_PORT", "7443")),
    )
    parser.add_argument(
        "--access-token",
        default=os.environ.get("ARUBA_BLE_PROXY_ACCESS_TOKEN") or None,
    )
    parser.add_argument(
        "--log-level",
        default=os.environ.get("ARUBA_BLE_PROXY_LOG_LEVEL", "info"),
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        default=os.environ.get("ARUBA_BLE_PROXY_SUMMARY", "").lower() in {"1", "true", "yes"},
        help="Log compact BLE summaries instead of every event",
    )
    return parser.parse_args(argv)


if __name__ == "__main__":
    main()
