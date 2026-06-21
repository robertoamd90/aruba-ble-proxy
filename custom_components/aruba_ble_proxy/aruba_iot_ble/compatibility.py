from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

SWITCHBOT_ADV_SERVICE_UUID = "0000fd3d-0000-1000-8000-00805f9b34fb"
SWITCHBOT_COMMAND_SERVICE_UUID = "cba20d00-224d-11e6-9fb8-0002a5d5c51b"
SWITCHBOT_WRITE_CHAR_UUID = "cba20002-224d-11e6-9fb8-0002a5d5c51b"
SWITCHBOT_READ_CHAR_UUID = "cba20003-224d-11e6-9fb8-0002a5d5c51b"


@dataclass(frozen=True)
class CompatibilityCharacteristicOverride:
    characteristic_uuid: str
    properties: tuple[str, ...]
    max_write_without_response_size: int = 20


@dataclass(frozen=True)
class CompatibilityServiceOverride:
    service_uuid: str
    characteristics: tuple[CompatibilityCharacteristicOverride, ...]


@dataclass(frozen=True)
class CompatibilityOverride:
    override_id: str
    vendor: str
    advertised_service_uuids: tuple[str, ...]
    missing_any_characteristic_uuids: tuple[str, ...]
    services: tuple[CompatibilityServiceOverride, ...]

    def matches(
        self,
        *,
        advertised_service_uuids: set[str],
        known_characteristic_uuids: set[str],
    ) -> bool:
        normalized_advertised = {
            _normalize_uuid(service_uuid) for service_uuid in advertised_service_uuids
        }
        normalized_known = {
            _normalize_uuid(characteristic_uuid)
            for characteristic_uuid in known_characteristic_uuids
        }
        if not all(
            _normalize_uuid(service_uuid) in normalized_advertised
            for service_uuid in self.advertised_service_uuids
        ):
            return False
        return any(
            _normalize_uuid(characteristic_uuid) not in normalized_known
            for characteristic_uuid in self.missing_any_characteristic_uuids
        )


class CompatibilityOverrideRegistry:
    def __init__(self, overrides: Iterable[CompatibilityOverride] | None = None) -> None:
        self._overrides = tuple(overrides or ())

    @property
    def overrides(self) -> tuple[CompatibilityOverride, ...]:
        return self._overrides

    def apply(
        self,
        services: Any,
        *,
        advertised_service_uuids: set[str],
        known_characteristic_uuids: set[str],
    ) -> list[str]:
        applied: list[str] = []
        for override in self._overrides:
            if not override.matches(
                advertised_service_uuids=advertised_service_uuids,
                known_characteristic_uuids=known_characteristic_uuids,
            ):
                continue
            if self._apply_override(
                services,
                override,
                known_characteristic_uuids=known_characteristic_uuids,
            ):
                applied.append(override.override_id)
        if applied:
            setattr(services, "_aruba_compatibility_overrides", tuple(applied))
        return applied

    def _apply_override(
        self,
        services: Any,
        override: CompatibilityOverride,
        *,
        known_characteristic_uuids: set[str],
    ) -> bool:
        from bleak.backends.characteristic import BleakGATTCharacteristic
        from bleak.backends.service import BleakGATTService

        next_handle = _next_handle(services)
        service_handles = _service_handles(services)
        applied = False

        for service_override in override.services:
            service_uuid = _normalize_uuid(service_override.service_uuid)
            service_handle = service_handles.get(service_uuid)
            if service_handle is None:
                service_handle = next_handle
                next_handle += 1
                service_handles[service_uuid] = service_handle
                services.add_service(
                    BleakGATTService(
                        obj={"source": "aruba_ble_proxy", "fallback": override.override_id},
                        handle=service_handle,
                        uuid=service_uuid,
                    )
                )

            service = services.get_service(service_uuid)
            if service is None:
                continue

            for characteristic_override in service_override.characteristics:
                characteristic_uuid = _normalize_uuid(
                    characteristic_override.characteristic_uuid
                )
                if characteristic_uuid in known_characteristic_uuids:
                    continue
                if services.get_characteristic(characteristic_uuid) is not None:
                    continue
                characteristic_handle = next_handle
                next_handle += 1
                services.add_characteristic(
                    BleakGATTCharacteristic(
                        obj={"source": "aruba_ble_proxy", "fallback": override.override_id},
                        handle=characteristic_handle,
                        uuid=characteristic_uuid,
                        properties=list(characteristic_override.properties),
                        max_write_without_response_size=(
                            lambda size=characteristic_override.max_write_without_response_size: size
                        ),
                        service=service,
                    )
                )
                applied = True
        return applied


def default_compatibility_registry() -> CompatibilityOverrideRegistry:
    return CompatibilityOverrideRegistry(
        overrides=(
            CompatibilityOverride(
                override_id="switchbot_fd3d_command_service",
                vendor="switchbot",
                advertised_service_uuids=(SWITCHBOT_ADV_SERVICE_UUID,),
                missing_any_characteristic_uuids=(
                    SWITCHBOT_WRITE_CHAR_UUID,
                    SWITCHBOT_READ_CHAR_UUID,
                ),
                services=(
                    CompatibilityServiceOverride(
                        service_uuid=SWITCHBOT_COMMAND_SERVICE_UUID,
                        characteristics=(
                            CompatibilityCharacteristicOverride(
                                characteristic_uuid=SWITCHBOT_WRITE_CHAR_UUID,
                                properties=("write-without-response",),
                            ),
                            CompatibilityCharacteristicOverride(
                                characteristic_uuid=SWITCHBOT_READ_CHAR_UUID,
                                properties=("notify", "read"),
                            ),
                        ),
                    ),
                ),
            ),
        ),
    )


def apply_gatt_overrides(
    services: Any,
    *,
    advertised_service_uuids: set[str],
    known_characteristic_uuids: set[str],
) -> list[str]:
    return default_compatibility_registry().apply(
        services,
        advertised_service_uuids=advertised_service_uuids,
        known_characteristic_uuids=known_characteristic_uuids,
    )


def _normalize_uuid(value: str) -> str:
    from uuid import UUID

    cleaned = value.strip().lower().replace("-", "").replace("{", "").replace("}", "")
    if len(cleaned) == 4:
        cleaned = f"0000{cleaned}00001000800000805f9b34fb"
    if len(cleaned) == 32:
        return str(UUID(hex=cleaned))
    return value.strip().lower()


def _next_handle(services: Any) -> int:
    characteristics = getattr(services, "characteristics", None)
    if isinstance(characteristics, dict) and characteristics:
        handles = [
            int(getattr(characteristic, "handle", 0))
            for characteristic in characteristics.values()
        ]
        if handles:
            return max(handles) + 1
    service_map = getattr(services, "services", None)
    if isinstance(service_map, dict) and service_map:
        handles = [
            int(getattr(service, "handle", 0))
            for service in service_map.values()
        ]
        if handles:
            return max(handles) + 1
    return 1


def _service_handles(services: Any) -> dict[str, int]:
    service_handles: dict[str, int] = {}
    service_map = getattr(services, "services", None)
    if not isinstance(service_map, dict):
        return service_handles
    for service in service_map.values():
        uuid = getattr(service, "uuid", None)
        handle = getattr(service, "handle", None)
        if uuid is None or handle is None:
            continue
        service_handles[_normalize_uuid(str(uuid))] = int(handle)
    return service_handles

