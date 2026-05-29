from __future__ import annotations

import hmac
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ble_parser import parse_advertisement_data
from .models import (
    ArubaActionResult,
    ArubaActionStatus,
    ArubaBleEvent,
    ArubaCharacteristic,
    ArubaDeviceStatus,
    ArubaStatusUpdate,
    BleFrameType,
    MacAddrType,
    Reporter,
)

LOGGER = logging.getLogger(__name__)


class ArubaProtoImportError(RuntimeError):
    pass


@dataclass
class ArubaTelemetryDecoder:
    access_token: str | None = None

    def __post_init__(self) -> None:
        self._pb = _load_aruba_pb2()
        self._warned_no_token = False

    def decode(self, message: bytes) -> list[ArubaBleEvent]:
        return self.decode_message(message).events

    def decode_message(self, message: bytes) -> "ArubaTelemetryMessage":
        telemetry = self._pb.telemetry_cls()
        telemetry.ParseFromString(message)

        if self.access_token is not None:
            received_token = getattr(telemetry.meta, "access_token", "")
            if not hmac.compare_digest(received_token, self.access_token):
                raise PermissionError("invalid Aruba access token")
        elif not self._warned_no_token:
            LOGGER.warning("Aruba access token validation is disabled")
            self._warned_no_token = True

        reporter = _reporter_from_pb(telemetry.reporter)
        LOGGER.info(
            "Aruba telemetry reporter=%s topic=%s reported=%d bleData=%d characteristics=%d results=%d wifiData=%d hasStatus=%s hasApHealth=%s",
            reporter.source,
            _enum_name_or_value(telemetry.meta, "nbTopic"),
            _repeated_len(telemetry, "reported"),
            _repeated_len(telemetry, "bleData"),
            _repeated_len(telemetry, "characteristics"),
            _repeated_len(telemetry, "results"),
            _repeated_len(telemetry, "wifiData"),
            _has_field(telemetry, "status"),
            _has_field(telemetry, "apHealth"),
        )

        events: list[ArubaBleEvent] = []

        for ble_data in telemetry.bleData:
            event = _event_from_pb(reporter, ble_data)
            if event is not None:
                events.append(event)

        results = [
            _action_result_from_pb(reporter, result)
            for result in getattr(telemetry, "results", [])
        ]
        characteristics = [
            _characteristic_from_pb(reporter, characteristic)
            for characteristic in getattr(telemetry, "characteristics", [])
        ]
        statuses = []
        if _has_field(telemetry, "status"):
            statuses.append(_status_update_from_pb(reporter, telemetry.status))

        return ArubaTelemetryMessage(
            reporter=reporter,
            events=events,
            action_results=results,
            characteristics=characteristics,
            statuses=statuses,
        )


@dataclass(frozen=True)
class ArubaTelemetryMessage:
    reporter: Reporter
    events: list[ArubaBleEvent]
    action_results: list[ArubaActionResult]
    characteristics: list[ArubaCharacteristic]
    statuses: list[ArubaStatusUpdate] | None = None


@dataclass(frozen=True)
class _ArubaPb2:
    telemetry_cls: type


def _load_aruba_pb2() -> _ArubaPb2:
    generated_proto_dir = Path(__file__).resolve().parent / "proto_generated"
    generated_proto_path = str(generated_proto_dir)
    if generated_proto_path not in sys.path:
        sys.path.insert(0, generated_proto_path)

    try:
        import aruba_iot_nb_pb2
    except ImportError as exc:
        raise ArubaProtoImportError(
            "Aruba protobuf modules are missing. Generate aruba_iot_*_pb2.py "
            "from Aruba's proto_files/source directory into "
            "custom_components/aruba_ble_proxy/proto_generated."
        ) from exc

    return _ArubaPb2(telemetry_cls=aruba_iot_nb_pb2.Telemetry)


def _event_from_pb(reporter: Reporter, ble_data: Any) -> ArubaBleEvent | None:
    if not getattr(ble_data, "mac", None):
        LOGGER.debug("Skipping BLE frame without MAC")
        return None

    payload = bytes(getattr(ble_data, "data", b""))
    if not payload:
        LOGGER.debug("Skipping BLE frame without payload")
        return None

    address = _format_mac(bytes(ble_data.mac))
    frame_type = _enum_or_int(BleFrameType, getattr(ble_data, "frameType", -1))
    address_type = _enum_or_int(MacAddrType, getattr(ble_data, "addrType", -1))
    apb_mac = _format_mac(bytes(ble_data.apbMac)) if getattr(ble_data, "apbMac", None) else None

    return ArubaBleEvent(
        reporter=reporter,
        address=address,
        frame_type=frame_type,
        rssi=int(getattr(ble_data, "rssi", 0)),
        address_type=address_type,
        apb_mac=apb_mac,
        payload=payload,
        advertisement=parse_advertisement_data(payload),
    )


def _action_result_from_pb(reporter: Reporter, result: Any) -> ArubaActionResult:
    status = int(getattr(result, "status", 0))
    return ArubaActionResult(
        reporter=reporter,
        action_id=str(getattr(result, "actionId", "")),
        action_type=_enum_name_or_value(result, "type"),
        device_mac=_format_mac(bytes(result.deviceMac)) if getattr(result, "deviceMac", None) else None,
        status=_enum_or_int(ArubaActionStatus, status),
        status_name=_enum_name_or_value(result, "status") or str(status),
        status_string=_optional_str(result, "statusString"),
        apb_mac=_format_mac(bytes(result.apbMac)) if getattr(result, "apbMac", None) else None,
    )


def _characteristic_from_pb(reporter: Reporter, characteristic: Any) -> ArubaCharacteristic:
    return ArubaCharacteristic(
        reporter=reporter,
        device_mac=(
            _format_mac(bytes(characteristic.deviceMac))
            if getattr(characteristic, "deviceMac", None)
            else None
        ),
        service_uuid=_format_uuid(bytes(characteristic.serviceUuid))
        if getattr(characteristic, "serviceUuid", None)
        else None,
        characteristic_uuid=_format_uuid(bytes(characteristic.characteristicUuid))
        if getattr(characteristic, "characteristicUuid", None)
        else None,
        value=bytes(getattr(characteristic, "value", b"")),
        description=_optional_str(characteristic, "description"),
        properties=tuple(
            _enum_repeated_name_or_value(characteristic, "properties", value)
            for value in getattr(characteristic, "properties", [])
        ),
    )


def _status_update_from_pb(reporter: Reporter, status: Any) -> ArubaStatusUpdate:
    status_value = int(getattr(status, "status", 0))
    mtu = None
    if _has_field(status, "connUpdate"):
        mtu_value = int(getattr(status.connUpdate, "mtu_value", 0))
        mtu = mtu_value or None
    return ArubaStatusUpdate(
        reporter=reporter,
        device_mac=_format_mac(bytes(status.deviceMac))
        if getattr(status, "deviceMac", None)
        else None,
        status=_enum_or_int(ArubaDeviceStatus, status_value),
        status_name=_enum_name_or_value(status, "status") or str(status_value),
        status_string=_optional_str(status, "statusString"),
        mtu=mtu,
    )


def _reporter_from_pb(reporter: Any) -> Reporter:
    return Reporter(
        name=_optional_str(reporter, "name"),
        mac=_format_mac(bytes(reporter.mac)) if getattr(reporter, "mac", None) else None,
        ipv4=_optional_str(reporter, "ipv4"),
        ipv6=_optional_str(reporter, "ipv6"),
        hardware_type=_optional_str(reporter, "hwType"),
        software_version=_optional_str(reporter, "swVersion"),
        software_build=_optional_str(reporter, "swBuild"),
        timestamp=int(reporter.time) if getattr(reporter, "time", None) else None,
    )


def _optional_str(obj: Any, field_name: str) -> str | None:
    value = getattr(obj, field_name, None)
    return value if value else None


def _format_mac(raw: bytes) -> str:
    return raw.hex(":")


def _format_uuid(raw: bytes) -> str:
    value = raw.hex()
    if len(value) == 4:
        return f"0000{value}-0000-1000-8000-00805f9b34fb"
    if len(value) == 32:
        return f"{value[0:8]}-{value[8:12]}-{value[12:16]}-{value[16:20]}-{value[20:32]}"
    return value


def _enum_or_int(enum_cls: type, value: int):
    try:
        return enum_cls(value)
    except ValueError:
        return value


def _enum_name_or_value(message: Any, field_name: str) -> str | int | None:
    if hasattr(message, "HasField") and not message.HasField(field_name):
        return None

    value = getattr(message, field_name, None)
    if value is None:
        return None
    if not hasattr(message, "DESCRIPTOR"):
        return value

    field = message.DESCRIPTOR.fields_by_name[field_name]
    enum_value = field.enum_type.values_by_number.get(value)
    return enum_value.name if enum_value is not None else value


def _enum_repeated_name_or_value(message: Any, field_name: str, value: int) -> str | int:
    if not hasattr(message, "DESCRIPTOR"):
        return value
    field = message.DESCRIPTOR.fields_by_name[field_name]
    enum_value = field.enum_type.values_by_number.get(value)
    return enum_value.name if enum_value is not None else value


def _repeated_len(message: Any, field_name: str) -> int:
    return len(getattr(message, field_name, []))


def _has_field(message: Any, field_name: str) -> bool:
    return bool(hasattr(message, "HasField") and message.HasField(field_name))
