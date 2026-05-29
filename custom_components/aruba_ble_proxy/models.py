from __future__ import annotations

from dataclasses import dataclass, field
from enum import IntEnum


class BleFrameType(IntEnum):
    ADV_IND = 0
    ADV_DIRECT_IND = 1
    ADV_NONCONN_IND = 2
    SCAN_RSP = 4
    ADV_SCAN_IND = 6


class MacAddrType(IntEnum):
    PUBLIC = 0
    STATIC = 1
    PRIVATE_NON_RESOLVABLE = 2
    PRIVATE_RESOLVABLE = 3


class ArubaActionStatus(IntEnum):
    FAILURE_GENERIC = 0
    SUCCESS = 1
    DEVICE_NOT_FOUND = 2
    AP_NOT_FOUND = 3
    ACTION_TIMEOUT = 4
    CONNECTION_ABORTED = 5
    AUTHENTICATION_FAILED = 6
    NOT_CONNECTED = 7
    PREVIOUS_ACTION_FAILED = 8
    ALREADY_CONNECTED = 9
    NO_MORE_CONNECTION_SLOTS = 10
    DECODING_FAILED = 11
    CHARACTERISTIC_NOT_FOUND = 12
    INVALID_REQUEST = 13
    GATT_ERROR = 14
    ENCRYPTION_FAILED = 15


class ArubaDeviceStatus(IntEnum):
    DEVICE_DISCONNECTED = 0
    INACTIVITY_TIMEOUT = 1
    CONNECTION_UPDATE = 2


@dataclass(frozen=True)
class Reporter:
    name: str | None
    mac: str | None
    ipv4: str | None
    ipv6: str | None
    hardware_type: str | None
    software_version: str | None
    software_build: str | None
    timestamp: int | None

    @property
    def source(self) -> str:
        return self.mac or self.name or "unknown-aruba-reporter"


@dataclass(frozen=True)
class BleAdvertisement:
    local_name: str | None = None
    service_uuids: tuple[str, ...] = ()
    manufacturer_data: dict[int, bytes] = field(default_factory=dict)
    service_data: dict[str, bytes] = field(default_factory=dict)
    raw_ad_structures: tuple[tuple[int, bytes], ...] = ()


@dataclass(frozen=True)
class ArubaBleEvent:
    reporter: Reporter
    address: str
    frame_type: BleFrameType | int
    rssi: int
    address_type: MacAddrType | int | None
    apb_mac: str | None
    payload: bytes
    advertisement: BleAdvertisement

    @property
    def source(self) -> str:
        return self.reporter.source


@dataclass(frozen=True)
class ArubaActionResult:
    reporter: Reporter
    action_id: str
    action_type: str | int | None
    device_mac: str | None
    status: ArubaActionStatus | int
    status_name: str
    status_string: str | None
    apb_mac: str | None

    @property
    def source(self) -> str:
        return self.reporter.source


@dataclass(frozen=True)
class ArubaCharacteristic:
    reporter: Reporter
    device_mac: str | None
    service_uuid: str | None
    characteristic_uuid: str | None
    value: bytes
    description: str | None
    properties: tuple[str | int, ...]

    @property
    def source(self) -> str:
        return self.reporter.source


@dataclass(frozen=True)
class ArubaStatusUpdate:
    reporter: Reporter
    device_mac: str | None
    status: ArubaDeviceStatus | int
    status_name: str
    status_string: str | None
    mtu: int | None

    @property
    def source(self) -> str:
        return self.reporter.source
