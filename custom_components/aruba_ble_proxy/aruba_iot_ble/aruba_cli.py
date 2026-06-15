from __future__ import annotations

import argparse
import re
import sys
from importlib.resources import files
from pathlib import Path
from typing import Iterable, TextIO

UUID16_RE = re.compile(r"^[0-9a-fA-F]{4}$")
BASE_UUID_RE = re.compile(
    r"^0000(?P<uuid>[0-9a-fA-F]{4})-0000-1000-8000-00805f9b34fb$",
    re.IGNORECASE,
)


def normalize_uuid16(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValueError("empty UUID")

    if cleaned.lower().startswith("0x"):
        cleaned = cleaned[2:]

    base_match = BASE_UUID_RE.match(cleaned)
    if base_match:
        cleaned = base_match.group("uuid")

    if not UUID16_RE.match(cleaned):
        raise ValueError(f"only 16-bit BLE service UUIDs are supported: {value!r}")

    return cleaned.upper()


def parse_uuid_file(path: Path) -> list[str]:
    uuids: list[str] = []
    seen: set[str] = set()

    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        value = line.split("#", 1)[0].strip()
        if not value:
            continue

        try:
            uuid = normalize_uuid16(value)
        except ValueError as err:
            raise ValueError(f"{path}:{line_number}: {err}") from err

        if uuid not in seen:
            seen.add(uuid)
            uuids.append(uuid)

    return uuids


def default_uuid_seed_path() -> Path:
    return Path(
        str(files("custom_components.aruba_ble_proxy.data").joinpath("ha_service_uuids_seed.txt"))
    )


def chunked(values: list[str], size: int) -> list[list[str]]:
    if size < 1:
        raise ValueError("chunk size must be at least 1")
    return [values[index : index + size] for index in range(0, len(values), size)]


def render_radio_profile(
    *,
    radio_profile: str,
    radio_instance: str = "internal",
    ble_opmode: str = "scanning",
    ble_txpower: int = 0,
    ble_console: str = "off",
) -> list[str]:
    return [
        f"iot radio-profile {radio_profile}",
        f"radio-instance {radio_instance}",
        "radio-mode ble",
        f"ble-opmode {ble_opmode}",
        f"ble-console {ble_console}",
        f"ble-txpower {ble_txpower}",
        "exit",
        f"iot use-radio-profile {radio_profile}",
    ]


def render_aruba_config(
    *,
    uuids: Iterable[str],
    name_prefix: str,
    endpoint_url: str,
    token: str,
    chunk_size: int = 10,
    start_index: int = 1,
    radio_profile: str | None = "ha-ble-radio",
    radio_instance: str = "internal",
    ble_opmode: str = "scanning",
    ble_txpower: int = 0,
    ble_console: str = "off",
) -> str:
    normalized = [normalize_uuid16(uuid) for uuid in uuids]
    chunks = chunked(normalized, chunk_size)

    lines = ["configure terminal"]
    if radio_profile:
        lines.extend(
            render_radio_profile(
                radio_profile=radio_profile,
                radio_instance=radio_instance,
                ble_opmode=ble_opmode,
                ble_txpower=ble_txpower,
                ble_console=ble_console,
            )
        )

    for offset, uuid_chunk in enumerate(chunks):
        profile_name = f"{name_prefix}-{start_index + offset:02d}"
        lines.extend(
            [
                f"iot transportProfile {profile_name}",
                "endpointType telemetry-websocket",
                f"endpointURL {endpoint_url}",
                f"endpointToken {token}",
                "bleDataForwarding",
                "blePeriodicTelemetryDisable",
                "no payloadContent",
                "no perFrameFiltering",
                "no companyIdentifierFilter",
                "no macOuiFilter",
                "no localNameFilter",
                f"serviceUUIDFilter {','.join(uuid_chunk)}",
                "exit",
                f"iot useTransportProfile {profile_name}",
            ]
        )

    lines.extend(["end", "commit apply"])
    return "\n".join(lines) + "\n"


def render_aruba_cleanup_config(
    *,
    name_prefix: str,
    profile_count: int,
    start_index: int = 1,
    radio_profile: str | None = "ha-ble-radio",
) -> str:
    if profile_count < 0:
        raise ValueError("profile count must be zero or greater")

    lines = ["configure terminal"]
    for offset in range(profile_count):
        profile_name = f"{name_prefix}-{start_index + offset:02d}"
        lines.append(f"no iot useTransportProfile {profile_name}")
    if radio_profile:
        lines.append(f"no iot use-radio-profile {radio_profile}")

    for offset in range(profile_count):
        profile_name = f"{name_prefix}-{start_index + offset:02d}"
        lines.append(f"no iot transportProfile {profile_name}")
    if radio_profile:
        lines.append(f"no iot radio-profile {radio_profile}")

    lines.extend(["end", "commit apply"])
    return "\n".join(lines) + "\n"


def render_transport_profiles(
    *,
    uuids: Iterable[str],
    name_prefix: str,
    endpoint_url: str,
    token: str,
    chunk_size: int = 10,
    start_index: int = 1,
) -> str:
    return render_aruba_config(
        uuids=uuids,
        name_prefix=name_prefix,
        endpoint_url=endpoint_url,
        token=token,
        chunk_size=chunk_size,
        start_index=start_index,
        radio_profile=None,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate Aruba Instant CLI commands for BLE service UUID filters"
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=default_uuid_seed_path(),
        help="Text file with one 16-bit BLE service UUID per line",
    )
    parser.add_argument("--name-prefix", default="ha-ble")
    parser.add_argument("--endpoint-url")
    parser.add_argument("--token")
    parser.add_argument("--chunk-size", type=int, default=10)
    parser.add_argument("--start-index", type=int, default=1)
    parser.add_argument(
        "--cleanup",
        action="store_true",
        help="Generate removal commands for the profiles this tool would create",
    )
    parser.add_argument(
        "--radio-profile",
        default="ha-ble-radio",
        help="IoT radio profile to create and enable",
    )
    parser.add_argument(
        "--no-radio-profile",
        action="store_true",
        help="Only generate transport profiles, for APs where the radio profile already exists",
    )
    parser.add_argument("--radio-instance", choices=["internal", "external"], default="internal")
    parser.add_argument(
        "--ble-opmode",
        choices=["beaconing", "scanning", "both"],
        default="scanning",
    )
    parser.add_argument("--ble-txpower", type=int, default=0)
    parser.add_argument(
        "--ble-console",
        choices=["dynamic", "off", "on"],
        default="off",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Optional file path. Defaults to stdout.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None, stdout: TextIO = sys.stdout) -> None:
    args = parse_args(argv)
    uuids = parse_uuid_file(args.input)
    radio_profile = None if args.no_radio_profile else args.radio_profile
    if args.cleanup:
        profile_count = len(chunked(uuids, args.chunk_size))
        config = render_aruba_cleanup_config(
            name_prefix=args.name_prefix,
            profile_count=profile_count,
            start_index=args.start_index,
            radio_profile=radio_profile,
        )
    else:
        if not args.endpoint_url or not args.token:
            raise SystemExit("--endpoint-url and --token are required unless --cleanup is used")
        config = render_aruba_config(
            uuids=uuids,
            name_prefix=args.name_prefix,
            endpoint_url=args.endpoint_url,
            token=args.token,
            chunk_size=args.chunk_size,
            start_index=args.start_index,
            radio_profile=radio_profile,
            radio_instance=args.radio_instance,
            ble_opmode=args.ble_opmode,
            ble_txpower=args.ble_txpower,
            ble_console=args.ble_console,
        )
    if args.output:
        args.output.write_text(config, encoding="utf-8")
        return

    stdout.write(config)


if __name__ == "__main__":
    main()
