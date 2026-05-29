from __future__ import annotations

from dataclasses import replace
import inspect
import logging
from typing import Any

from .ha_payload import BluetoothPayload

_LOGGER = logging.getLogger(__name__)


class ArubaBleRemoteScanner:
    """Home Assistant Bluetooth scanner backed by one Aruba AP."""

    def __init__(self, source: str, runtime: Any | None = None, connectable: bool = False) -> None:
        try:
            from homeassistant.components.bluetooth import (
                BaseHaRemoteScanner,
                BluetoothScanningMode,
            )
        except (AttributeError, ImportError):
            from habluetooth import BaseHaRemoteScanner, BluetoothScanningMode

        connector = None
        scanner_ref = None
        if connectable and runtime is not None:
            try:
                from .active_client import create_aruba_bleak_client

                def can_connect() -> bool:
                    return runtime.can_connect_source(
                        source
                    ) and _connections_in_progress(scanner_ref) == 0

                connector = _ha_bluetooth_connector(
                    client=create_aruba_bleak_client(runtime, source),
                    source=source,
                    can_connect=can_connect,
                )
            except Exception:
                _LOGGER.exception(
                    "Failed to create Aruba active BLE connector for %s; "
                    "falling back to passive scanner",
                    source,
                )

        class _Scanner(BaseHaRemoteScanner):
            def get_allocations(self):
                return _active_allocations(
                    adapter=self.adapter,
                    active_devices=(
                        runtime.active_devices_for_source(source)
                        if runtime is not None
                        and hasattr(runtime, "active_devices_for_source")
                        else []
                    ),
                    in_progress=getattr(self, "_connect_in_progress", {}),
                    slots=1 if connector is not None else 0,
                )

        scanner_name = f"Aruba AP {source}"
        self._scanner = _build_remote_scanner(
            _Scanner,
            source=source,
            name=scanner_name,
            connector=connector,
            mode=BluetoothScanningMode.PASSIVE,
        )
        self._scanner.name = scanner_name
        self._scanner.source = source
        self._scanner.adapter = source
        self._scanner.details = replace(self._scanner.details, name=scanner_name)
        scanner_ref = self._scanner

    @property
    def scanner(self) -> Any:
        return self._scanner

    def async_setup(self):
        return self._scanner.async_setup()

    def async_on_payload(self, payload: BluetoothPayload) -> None:
        if hasattr(self._scanner, "_async_on_advertisement_internal"):
            _call_advertisement_method(
                self._scanner._async_on_advertisement_internal,
                payload,
                include_raw=True,
            )
            return

        _call_advertisement_method(
            self._scanner._async_on_advertisement,
            payload,
            include_raw=False,
        )

    @property
    def connectable(self) -> bool:
        return bool(getattr(self._scanner, "connectable", False))


def _ha_bluetooth_connector(*, client: type, source: str, can_connect):
    try:
        from homeassistant.components.bluetooth import HaBluetoothConnector
    except (AttributeError, ImportError):
        try:
            from habluetooth import HaBluetoothConnector
        except ImportError:
            from habluetooth.models import HaBluetoothConnector

    return HaBluetoothConnector(client=client, source=source, can_connect=can_connect)


def _build_remote_scanner(
    scanner_cls: type,
    *,
    source: str,
    name: str,
    connector: Any,
    mode: Any,
):
    common = {
        "connector": connector,
        "connectable": connector is not None,
        "requested_mode": mode,
        "current_mode": mode,
    }
    try:
        return scanner_cls(
            scanner_id=source,
            name=name,
            **common,
        )
    except TypeError as err:
        if "scanner_id" not in str(err) and "name" not in str(err):
            raise
        return scanner_cls(
            source=source,
            adapter=source,
            **common,
        )


def _connections_in_progress(scanner: Any | None) -> int:
    if scanner is None:
        return 0
    get_count = getattr(scanner, "_connections_in_progress", None)
    if get_count is not None:
        return int(get_count())
    return sum(getattr(scanner, "_connect_in_progress", {}).values())


def _call_advertisement_method(method: Any, payload: BluetoothPayload, *, include_raw: bool) -> None:
    args = (
        payload.address,
        payload.rssi,
        payload.name,
        payload.service_uuids,
        payload.service_data,
        payload.manufacturer_data,
        payload.tx_power,
        {},
        payload.time,
    )
    if not include_raw:
        method(*args)
        return

    args_with_raw = (*args, payload.raw)
    try:
        signature = inspect.signature(method)
    except (TypeError, ValueError):
        method(*args_with_raw)
        return
    try:
        signature.bind(*args_with_raw)
    except TypeError:
        method(*args)
    else:
        method(*args_with_raw)


def _active_allocations(
    *,
    adapter: str,
    active_devices: list[str],
    in_progress: dict[str, int],
    slots: int,
):
    try:
        from bleak_retry_connector import Allocations
    except ImportError:
        return None

    allocated = sorted(
        {
            *active_devices,
            *(
                address
                for address, count in in_progress.items()
                if count > 0
            ),
        }
    )
    return Allocations(
        adapter=adapter,
        slots=slots,
        free=max(0, slots - len(allocated)),
        allocated=allocated,
    )
