from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import UTC, datetime
from time import monotonic
from typing import Any

from .active import (
    ACTION_BLE_CONNECT,
    ACTION_BLE_DISCONNECT,
    ACTION_GATT_INDICATION,
    ACTION_GATT_NOTIFICATION,
    ACTION_GATT_READ,
    ACTION_GATT_WRITE,
    ACTION_GATT_WRITE_WITH_RESPONSE,
    ArubaBleActionRequest,
    encode_action_message,
)
from .aruba_proto import ArubaTelemetryMessage
from .const import (
    CONF_AP_SOURCE,
    CONF_ENTRY_TYPE,
    CONF_PARENT_ENTRY_ID,
    DOMAIN,
    ENTRY_TYPE_AP_SOURCE,
)
from .ha_payload import BluetoothPayload, event_to_bluetooth_payload
from .models import ArubaActionResult, ArubaBleEvent, ArubaCharacteristic, ArubaStatusUpdate
from .server import ArubaBleReceiver

_LOGGER = logging.getLogger(__name__)

DISCONNECTED_DEVICE_STATUSES = {
    "deviceDisconnected",
    "inactivityTimeout",
    "sourceDisconnected",
}

CONNECT_SUCCESS_STATUSES = {"success", "alreadyConnected"}
DISCONNECT_SUCCESS_STATUSES = {
    "success",
    "notConnected",
    *DISCONNECTED_DEVICE_STATUSES,
}

PASSIVE_SENSOR_UPDATE_INTERVAL = 30.0


@dataclass
class RuntimeStats:
    events: int = 0
    addresses: set[str] = field(default_factory=set)
    sources: set[str] = field(default_factory=set)
    service_data: set[str] = field(default_factory=set)
    manufacturer_ids: set[int] = field(default_factory=set)
    local_names: set[str] = field(default_factory=set)
    bluetooth_forwards: int = 0
    bluetooth_forward_errors: int = 0
    active_actions_sent: int = 0
    active_action_send_errors: int = 0
    active_action_results: int = 0
    active_action_failures: int = 0
    active_action_timeouts: int = 0
    active_action_cancellations: int = 0
    active_action_orphan_results: int = 0
    active_status_updates: int = 0
    active_disconnect_statuses: int = 0
    active_source_disconnects: int = 0
    active_characteristics: int = 0
    active_characteristic_waits: int = 0
    active_characteristic_wait_timeouts: int = 0
    active_connectable_scanners: int = 0
    active_notifications_enabled: int = 0
    active_notification_updates: int = 0
    active_notification_callback_errors: int = 0
    last_seen: str | None = None
    last_address: str | None = None
    last_source: str | None = None
    last_rssi: int | None = None
    last_local_name: str | None = None
    last_service_data: list[str] = field(default_factory=list)
    last_manufacturer_ids: list[int] = field(default_factory=list)
    last_bluetooth_error: str | None = None
    last_active_action_id: str | None = None
    last_active_action_type: str | None = None
    last_active_action_status: str | None = None
    last_active_action_error: str | None = None
    last_active_action_duration_ms: int | None = None
    slowest_active_action_type: str | None = None
    slowest_active_action_status: str | None = None
    slowest_active_action_duration_ms: int | None = None
    active_action_duration_total_ms: int = 0
    last_active_status_source: str | None = None
    last_active_status_device: str | None = None
    last_active_status: str | None = None
    last_active_status_string: str | None = None
    last_active_mtu: int | None = None
    last_active_characteristic_device: str | None = None
    last_active_characteristic_service: str | None = None
    last_active_characteristic_uuid: str | None = None
    last_active_characteristic_value: str | None = None
    last_active_characteristic_wait_status: str | None = None
    last_active_characteristic_wait_duration_ms: int | None = None
    slowest_active_characteristic_wait_status: str | None = None
    slowest_active_characteristic_wait_duration_ms: int | None = None
    active_characteristic_wait_duration_total_ms: int = 0
    last_active_notification_error: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "events": self.events,
            "addresses": len(self.addresses),
            "sources": sorted(self.sources),
            "service_data": sorted(self.service_data),
            "manufacturer_ids": sorted(self.manufacturer_ids),
            "local_names": sorted(self.local_names),
            "bluetooth_forwards": self.bluetooth_forwards,
            "bluetooth_forward_errors": self.bluetooth_forward_errors,
            "active_actions_sent": self.active_actions_sent,
            "active_action_send_errors": self.active_action_send_errors,
            "active_action_results": self.active_action_results,
            "active_action_failures": self.active_action_failures,
            "active_action_timeouts": self.active_action_timeouts,
            "active_action_cancellations": self.active_action_cancellations,
            "active_action_orphan_results": self.active_action_orphan_results,
            "active_status_updates": self.active_status_updates,
            "active_disconnect_statuses": self.active_disconnect_statuses,
            "active_source_disconnects": self.active_source_disconnects,
            "active_characteristics": self.active_characteristics,
            "active_characteristic_waits": self.active_characteristic_waits,
            "active_characteristic_wait_timeouts": self.active_characteristic_wait_timeouts,
            "active_connectable_scanners": self.active_connectable_scanners,
            "active_notifications_enabled": self.active_notifications_enabled,
            "active_notification_updates": self.active_notification_updates,
            "active_notification_callback_errors": self.active_notification_callback_errors,
            "last_seen": self.last_seen,
            "last_address": self.last_address,
            "last_source": self.last_source,
            "last_rssi": self.last_rssi,
            "last_local_name": self.last_local_name,
            "last_service_data": self.last_service_data,
            "last_manufacturer_ids": self.last_manufacturer_ids,
            "last_bluetooth_error": self.last_bluetooth_error,
            "last_active_action_id": self.last_active_action_id,
            "last_active_action_type": self.last_active_action_type,
            "last_active_action_status": self.last_active_action_status,
            "last_active_action_error": self.last_active_action_error,
            "last_active_action_duration_ms": self.last_active_action_duration_ms,
            "slowest_active_action_type": self.slowest_active_action_type,
            "slowest_active_action_status": self.slowest_active_action_status,
            "slowest_active_action_duration_ms": self.slowest_active_action_duration_ms,
            "active_action_duration_total_ms": self.active_action_duration_total_ms,
            "last_active_status_source": self.last_active_status_source,
            "last_active_status_device": self.last_active_status_device,
            "last_active_status": self.last_active_status,
            "last_active_status_string": self.last_active_status_string,
            "last_active_mtu": self.last_active_mtu,
            "last_active_characteristic_device": self.last_active_characteristic_device,
            "last_active_characteristic_service": self.last_active_characteristic_service,
            "last_active_characteristic_uuid": self.last_active_characteristic_uuid,
            "last_active_characteristic_value": self.last_active_characteristic_value,
            "last_active_characteristic_wait_status": self.last_active_characteristic_wait_status,
            "last_active_characteristic_wait_duration_ms": (
                self.last_active_characteristic_wait_duration_ms
            ),
            "slowest_active_characteristic_wait_status": (
                self.slowest_active_characteristic_wait_status
            ),
            "slowest_active_characteristic_wait_duration_ms": (
                self.slowest_active_characteristic_wait_duration_ms
            ),
            "active_characteristic_wait_duration_total_ms": (
                self.active_characteristic_wait_duration_total_ms
            ),
            "last_active_notification_error": self.last_active_notification_error,
        }


@dataclass
class _ActiveOperationSlot:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    users: int = 0


@dataclass(frozen=True)
class _PendingActionContext:
    ap_mac: str
    device_mac: str
    action_type: str
    started_at: float


class _CharacteristicWaitFailed(Exception):
    def __init__(self, status: str, status_string: str | None = None) -> None:
        super().__init__(status)
        self.status = status
        self.status_string = status_string


class ArubaBleProxyRuntime:
    def __init__(
        self,
        *,
        hass: Any,
        host: str,
        port: int,
        access_token: str,
        enable_active_ble: bool = True,
        active_connection_slots: int = 1,
    ) -> None:
        self.hass = hass
        self.host = host
        self.port = port
        self.access_token = access_token
        self.enable_active_ble = enable_active_ble
        self.active_connection_slots = max(1, int(active_connection_slots))
        self.stats = RuntimeStats()
        self._receiver = ArubaBleReceiver(
            host=host,
            port=port,
            access_token=access_token,
            event_handler=self._async_handle_event,
            message_handler=self._async_handle_message,
            source_disconnect_handler=self._handle_source_disconnect,
        )
        self._task: asyncio.Task | None = None
        self._listeners: list[Callable[[], None]] = []
        self._bluetooth_callback: Callable[[Any], None] | None = None
        self._entry_id: str | None = None
        self._source_entry_ids: dict[str, str] = {}
        self._register_scanner: Callable[..., Callable[[], None]] | None = None
        self._scanner_unsubs: dict[str, list[Callable[[], None]]] = {}
        self._remote_scanners: dict[str, Any] = {}
        self._pending_actions: dict[str, asyncio.Future] = {}
        self._pending_action_contexts: dict[str, _PendingActionContext] = {}
        self._active_operation_slots: dict[tuple[str, str], _ActiveOperationSlot] = {}
        self._pending_characteristics: dict[
            tuple[str, str, str, str], list[asyncio.Future]
        ] = {}
        self._pending_device_characteristics: dict[
            tuple[str | None, str], list[asyncio.Future]
        ] = {}
        self._last_characteristics: dict[
            tuple[str, str, str, str], ArubaCharacteristic
        ] = {}
        self._device_advertised_service_uuids: dict[str, set[str]] = {}
        self._device_connection_statuses: dict[tuple[str, str], str] = {}
        self._device_mtu: dict[tuple[str, str], int] = {}
        self._active_device_keys_by_source: dict[str, set[tuple[str, str]]] = {}
        self._device_disconnect_listeners: dict[
            tuple[str, str],
            list[Callable[[ArubaStatusUpdate], None]],
        ] = {}
        self._notification_callbacks: dict[
            tuple[str, str, str, str],
            list[Callable[[ArubaCharacteristic], None]],
        ] = {}
        self._last_passive_listener_update = 0.0

    async def async_start(self, entry: Any | None = None) -> None:
        from homeassistant.components import bluetooth

        self._entry_id = getattr(entry, "entry_id", None)
        self._bluetooth_callback = bluetooth.async_get_advertisement_callback(self.hass)
        self._register_scanner = getattr(bluetooth, "async_register_scanner", None)
        if entry is not None and hasattr(entry, "async_create_background_task"):
            self._task = entry.async_create_background_task(
                self.hass,
                self._receiver.run(),
                "Aruba BLE Proxy receiver",
            )
        elif hasattr(self.hass, "async_create_background_task"):
            self._task = self.hass.async_create_background_task(
                self._receiver.run(),
                "Aruba BLE Proxy receiver",
            )
        else:
            self._task = self.hass.async_create_task(
                self._receiver.run(),
                "Aruba BLE Proxy receiver",
            )
        await asyncio.sleep(0)
        if self._task.done():
            self._task.result()
        self._notify_listeners()

    async def async_stop(self) -> None:
        await self._async_disconnect_active_devices_on_stop()
        self._unregister_scanners()
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _async_disconnect_active_devices_on_stop(self) -> None:
        active_keys = sorted(
            key
            for source_devices in self._active_device_keys_by_source.values()
            for key in source_devices
        )
        for source, device_mac in active_keys:
            try:
                await self._async_send_aruba_action_unlocked(
                    ap_mac=source,
                    request=ArubaBleActionRequest(
                        action_type=ACTION_BLE_DISCONNECT,
                        device_mac=device_mac,
                        timeout=5,
                    ),
                    wait_result=False,
                )
            except Exception:
                _LOGGER.exception(
                    "Failed to send best-effort Aruba BLE disconnect for %s via %s",
                    device_mac,
                    source,
                )
            self.stats.active_disconnect_statuses += 1
            self._mark_device_disconnected(
                (source, device_mac),
                ArubaStatusUpdate(
                    reporter=self._synthetic_reporter_for_source(source),
                    device_mac=device_mac,
                    status=0,
                    status_name="deviceDisconnected",
                    status_string="Aruba runtime stopped",
                    mtu=None,
                ),
            )

    def async_add_listener(self, listener: Callable[[], None]) -> Callable[[], None]:
        self._listeners.append(listener)

        def remove_listener() -> None:
            if listener in self._listeners:
                self._listeners.remove(listener)

        return remove_listener

    def add_device_disconnect_listener(
        self,
        source: str,
        device_mac: str,
        listener: Callable[[ArubaStatusUpdate], None],
    ) -> Callable[[], None]:
        key = _device_key(source, device_mac)
        listeners = self._device_disconnect_listeners.setdefault(key, [])
        listeners.append(listener)

        def remove_listener() -> None:
            current = self._device_disconnect_listeners.get(key)
            if current is None or listener not in current:
                return
            current.remove(listener)
            if not current:
                self._device_disconnect_listeners.pop(key, None)

        return remove_listener

    async def _async_handle_event(self, event: ArubaBleEvent) -> None:
        self._update_stats(event)
        payload = event_to_bluetooth_payload(event)
        if not await self._async_forward_to_remote_scanner(payload):
            self._async_forward_to_bluetooth(payload)
        self._notify_passive_listeners()

    async def _async_handle_message(self, message: ArubaTelemetryMessage) -> None:
        for characteristic in message.characteristics:
            self._handle_characteristic(characteristic)
        for status in message.statuses or []:
            self._handle_status_update(status)
        for result in message.action_results:
            self.stats.active_action_results += 1
            self.stats.last_active_action_id = result.action_id
            self.stats.last_active_action_type = str(result.action_type or "unknown")
            self.stats.last_active_action_status = result.status_name
            future = self._pending_actions.pop(result.action_id, None)
            context = self._pending_action_contexts.pop(result.action_id, None)
            if context is not None:
                self._record_active_action_duration(
                    action_type=context.action_type,
                    status=result.status_name,
                    started_at=context.started_at,
                )
            if future is None:
                self.stats.active_action_orphan_results += 1
                if _is_successful_action_result(result, context):
                    self._handle_successful_action_result(result, context)
                else:
                    self.stats.active_action_failures += 1
                    self.stats.last_active_action_error = _format_action_error(
                        result.status_name,
                        result.status_string,
                    )
                continue
            if _is_successful_action_result(result, context):
                self.stats.last_active_action_error = None
                self._handle_successful_action_result(result, context)
            else:
                self.stats.active_action_failures += 1
                self.stats.last_active_action_error = _format_action_error(
                    result.status_name,
                    result.status_string,
                )
            if future is not None and not future.done():
                future.set_result(result)
        if message.action_results or message.characteristics or message.statuses:
            self._notify_listeners()

    def _handle_characteristic(self, characteristic: ArubaCharacteristic) -> None:
        source = _normalize_mac(characteristic.source)
        device_mac = _normalize_mac(characteristic.device_mac)
        characteristic_uuid = (
            _normalize_uuid(characteristic.characteristic_uuid)
            if characteristic.characteristic_uuid
            else None
        )
        key = _characteristic_key(
            characteristic.source,
            characteristic.device_mac,
            characteristic.service_uuid,
            characteristic.characteristic_uuid,
        )
        if source is None or device_mac is None or characteristic_uuid is None:
            return
        self.stats.active_characteristics += 1
        self.stats.last_active_characteristic_device = device_mac
        self.stats.last_active_characteristic_service = key[2] if key else None
        self.stats.last_active_characteristic_uuid = characteristic_uuid
        self.stats.last_active_characteristic_value = characteristic.value.hex()
        futures = []
        if key is not None:
            self._last_characteristics[key] = characteristic
            futures = self._pending_characteristics.pop(key, [])
        for future in futures:
            if not future.done():
                future.set_result(characteristic)
        device_futures = [
            *self._pending_device_characteristics.pop((source, device_mac), []),
            *self._pending_device_characteristics.pop((None, device_mac), []),
        ]
        for future in device_futures:
            if not future.done():
                future.set_result(
                    self.characteristics_for_device(device_mac, source=source)
                    or self.characteristics_for_device(device_mac)
                )
        callbacks = self._notification_callbacks_for(
            source,
            device_mac,
            key[2] if key else None,
            characteristic_uuid,
        )
        if callbacks:
            self.stats.active_notification_updates += 1
        for callback in callbacks:
            try:
                callback(characteristic)
            except Exception as err:
                self.stats.active_notification_callback_errors += 1
                self.stats.last_active_notification_error = f"{type(err).__name__}: {err}"
                _LOGGER.exception("Aruba BLE notification callback failed")

    def _notification_callbacks_for(
        self,
        source: str,
        device_mac: str,
        service_uuid: str | None,
        characteristic_uuid: str,
    ) -> list[Callable[[ArubaCharacteristic], None]]:
        callbacks: list[Callable[[ArubaCharacteristic], None]] = []
        seen: set[int] = set()
        for (
            registered_source,
            registered_device,
            registered_service,
            registered_characteristic,
        ), registered_callbacks in self._notification_callbacks.items():
            if registered_source != source or registered_device != device_mac:
                continue
            if registered_characteristic != characteristic_uuid:
                continue
            if service_uuid is not None and registered_service != service_uuid:
                _LOGGER.debug(
                    "Dispatching Aruba BLE notification despite service UUID mismatch: "
                    "registered=%s received=%s characteristic=%s",
                    registered_service,
                    service_uuid,
                    characteristic_uuid,
                )
            for callback in registered_callbacks:
                callback_id = id(callback)
                if callback_id in seen:
                    continue
                callbacks.append(callback)
                seen.add(callback_id)
        return callbacks

    def _handle_status_update(self, status: ArubaStatusUpdate) -> None:
        self.stats.active_status_updates += 1
        self.stats.last_active_status_source = _normalize_mac(status.source)
        self.stats.last_active_status_device = _normalize_mac(status.device_mac)
        self.stats.last_active_status = status.status_name
        self.stats.last_active_status_string = status.status_string
        if status.mtu is not None:
            self.stats.last_active_mtu = status.mtu

        if not status.device_mac:
            return

        key = _device_key(status.source, status.device_mac)
        if status.status_name in DISCONNECTED_DEVICE_STATUSES:
            self.stats.active_disconnect_statuses += 1
            self._mark_device_disconnected(key, status)
        elif status.status_name == "connectionUpdate":
            self._device_connection_statuses.pop(key, None)
            self._active_device_keys_by_source.setdefault(key[0], set()).add(key)
            if status.mtu is not None:
                self._device_mtu[key] = status.mtu

    def _handle_successful_action_result(
        self,
        result: Any,
        context: _PendingActionContext | None = None,
    ) -> None:
        device_mac = result.device_mac or (context.device_mac if context else None)
        action_type = result.action_type or (context.action_type if context else None)
        source = context.ap_mac if context is not None else result.source
        if not device_mac:
            return
        if action_type == ACTION_BLE_CONNECT:
            key = _device_key(source, device_mac)
            self._device_connection_statuses.pop(key, None)
            self._active_device_keys_by_source.setdefault(key[0], set()).add(key)
        elif action_type == ACTION_BLE_DISCONNECT:
            key = _device_key(source, device_mac)
            self._mark_device_disconnected(
                key,
                ArubaStatusUpdate(
                    reporter=result.reporter or self._synthetic_reporter_for_source(source),
                    device_mac=device_mac,
                    status=0,
                    status_name="deviceDisconnected",
                    status_string=result.status_string,
                    mtu=None,
                ),
            )

    def _handle_source_disconnect(self, source: str) -> None:
        normalized_source = _normalize_mac(source) or source.upper()
        self.stats.active_source_disconnects += 1
        device_keys = set(self._active_device_keys_by_source.get(normalized_source, set()))
        device_keys.update(
            key
            for key in self._device_disconnect_listeners
            if key[0] == normalized_source
        )
        device_keys.update(
            (key[0], key[1])
            for key in self._pending_characteristics
            if key[0] == normalized_source
        )
        device_keys.update(
            key
            for key in self._pending_device_characteristics
            if key[0] == normalized_source and key[1] is not None
        )
        device_keys.update(
            (key[0], key[1])
            for key in self._notification_callbacks
            if key[0] == normalized_source
        )
        device_keys.update(
            (key[0], key[1])
            for key in self._last_characteristics
            if key[0] == normalized_source
        )
        for key in sorted(device_keys):
            _, device_mac = key
            self.stats.active_disconnect_statuses += 1
            self.stats.last_active_status_source = normalized_source
            self.stats.last_active_status_device = device_mac
            self.stats.last_active_status = "sourceDisconnected"
            self.stats.last_active_status_string = "Aruba WebSocket source disconnected"
            self._mark_device_disconnected(
                key,
                ArubaStatusUpdate(
                    reporter=self._synthetic_reporter_for_source(normalized_source),
                    device_mac=device_mac,
                    status=-1,
                    status_name="sourceDisconnected",
                    status_string="Aruba WebSocket source disconnected",
                    mtu=None,
                ),
            )
        self._fail_pending_actions_for_source(normalized_source)
        self._notify_listeners()

    def _fail_pending_actions_for_source(self, source: str) -> None:
        for action_id, context in list(self._pending_action_contexts.items()):
            if context.ap_mac != source:
                continue
            future = self._pending_actions.pop(action_id, None)
            self._pending_action_contexts.pop(action_id, None)
            if future is None or future.done():
                continue
            result = ArubaActionResult(
                reporter=self._synthetic_reporter_for_source(source),
                action_id=action_id,
                action_type=context.action_type,
                device_mac=context.device_mac,
                status=-1,
                status_name="sourceDisconnected",
                status_string="Aruba WebSocket source disconnected",
                apb_mac=None,
            )
            self.stats.last_active_action_id = action_id
            self.stats.last_active_action_status = "sourceDisconnected"
            if _is_successful_action_result(result, context):
                self.stats.last_active_action_error = None
            else:
                self.stats.active_action_failures += 1
                self.stats.last_active_action_error = (
                    "sourceDisconnected: Aruba WebSocket source disconnected"
                )
            future.set_result(result)

    def _mark_device_disconnected(
        self,
        key: tuple[str, str],
        status: ArubaStatusUpdate,
    ) -> None:
        self._device_connection_statuses[key] = status.status_name
        self._device_mtu.pop(key, None)
        source_devices = self._active_device_keys_by_source.get(key[0])
        if source_devices is not None:
            source_devices.discard(key)
            if not source_devices:
                self._active_device_keys_by_source.pop(key[0], None)
        self._forget_device_notification_callbacks(key[0], key[1])
        self._forget_device_characteristics(key[0], key[1])
        self._fail_pending_actions_for_device(key, status)
        self._fail_pending_characteristic_reads_for_device(key, status)
        self._resolve_device_characteristic_waiters(key[0], key[1])
        self._notify_device_disconnect_listeners(key, status)

    def _fail_pending_actions_for_device(
        self,
        key: tuple[str, str],
        status: ArubaStatusUpdate,
    ) -> None:
        source, device_mac = key
        for action_id, context in list(self._pending_action_contexts.items()):
            if context.ap_mac != source or context.device_mac != device_mac:
                continue
            future = self._pending_actions.pop(action_id, None)
            self._pending_action_contexts.pop(action_id, None)
            if future is None or future.done():
                continue
            result = ArubaActionResult(
                reporter=status.reporter,
                action_id=action_id,
                action_type=context.action_type,
                device_mac=device_mac,
                status=status.status,
                status_name=status.status_name,
                status_string=status.status_string,
                apb_mac=None,
            )
            self.stats.last_active_action_id = action_id
            self.stats.last_active_action_status = status.status_name
            if _is_successful_action_result(result, context):
                self.stats.last_active_action_error = None
            else:
                self.stats.active_action_failures += 1
                self.stats.last_active_action_error = _format_action_error(
                    status.status_name,
                    status.status_string,
                )
            future.set_result(result)

    def _fail_pending_characteristic_reads_for_device(
        self,
        key: tuple[str, str],
        status: ArubaStatusUpdate,
    ) -> None:
        source, device_mac = key
        for characteristic_key, futures in list(self._pending_characteristics.items()):
            if characteristic_key[0] != source or characteristic_key[1] != device_mac:
                continue
            self._pending_characteristics.pop(characteristic_key, None)
            for future in futures:
                if not future.done():
                    future.set_exception(
                        _CharacteristicWaitFailed(
                            status.status_name,
                            status.status_string,
                        )
                    )

    def _forget_device_notification_callbacks(self, source: str, device_mac: str) -> None:
        normalized_source = _normalize_mac(source) or source.upper()
        normalized = _normalize_mac(device_mac)
        for key, callbacks in list(self._notification_callbacks.items()):
            if key[0] != normalized_source or key[1] != normalized:
                continue
            self.stats.active_notifications_enabled = max(
                0,
                self.stats.active_notifications_enabled - len(callbacks),
            )
            self._notification_callbacks.pop(key, None)

    def _forget_device_characteristics(self, source: str, device_mac: str) -> None:
        normalized_source = _normalize_mac(source) or source.upper()
        normalized = _normalize_mac(device_mac)
        for key in list(self._last_characteristics):
            if key[0] == normalized_source and key[1] == normalized:
                self._last_characteristics.pop(key, None)

    def clear_device_characteristics(self, source: str, device_mac: str) -> bool:
        normalized_source = _normalize_mac(source) or source.upper()
        normalized = _normalize_mac(device_mac)
        removed = False
        for key in list(self._last_characteristics):
            if key[0] == normalized_source and key[1] == normalized:
                self._last_characteristics.pop(key, None)
                removed = True
        return removed

    def _resolve_device_characteristic_waiters(self, source: str, device_mac: str) -> None:
        normalized_source = _normalize_mac(source) or source.upper()
        normalized = _normalize_mac(device_mac)
        futures = [
            *self._pending_device_characteristics.pop((normalized_source, normalized), []),
            *self._pending_device_characteristics.pop((None, normalized), []),
        ]
        for future in futures:
            if not future.done():
                future.set_result([])

    def _notify_device_disconnect_listeners(
        self,
        key: tuple[str, str],
        status: ArubaStatusUpdate,
    ) -> None:
        for listener in list(self._device_disconnect_listeners.get(key, [])):
            try:
                listener(status)
            except Exception:
                _LOGGER.exception("Aruba BLE device disconnect listener failed")

    def is_device_active(self, source: str, device_mac: str) -> bool:
        key = _device_key(source, device_mac)
        return (
            key in self._active_device_keys_by_source.get(key[0], set())
            and self._device_connection_statuses.get(key) not in DISCONNECTED_DEVICE_STATUSES
        )

    def mtu_for_device(self, source: str, device_mac: str) -> int | None:
        return self._device_mtu.get(_device_key(source, device_mac))

    def _synthetic_reporter_for_source(self, source: str):
        from .models import Reporter

        return Reporter(
            name=None,
            mac=source,
            ipv4=None,
            ipv6=None,
            hardware_type=None,
            software_version=None,
            software_build=None,
            timestamp=None,
        )

    async def async_send_aruba_action(
        self,
        *,
        ap_mac: str,
        request: ArubaBleActionRequest,
        wait_result: bool = True,
    ) -> dict[str, Any]:
        async with self._active_operation(ap_mac, request.device_mac):
            local_response = self._local_connect_slot_response(ap_mac, request)
            if local_response is not None:
                return local_response
            return await self._async_send_aruba_action_unlocked(
                ap_mac=ap_mac,
                request=request,
                wait_result=wait_result,
            )

    def _local_connect_slot_response(
        self,
        ap_mac: str,
        request: ArubaBleActionRequest,
    ) -> dict[str, Any] | None:
        if request.action_type != ACTION_BLE_CONNECT:
            return None

        source = _normalize_mac(ap_mac) or ap_mac.upper()
        device_mac = _normalize_mac(request.device_mac) or request.device_mac.upper()
        active_devices = self.active_devices_for_source(source)
        pending_devices = self.pending_connect_devices_for_source(source)
        slot_devices = sorted({*active_devices, *pending_devices})
        if not slot_devices:
            return None

        if device_mac in active_devices:
            status = "alreadyConnected"
            status_string = "Device is already connected through this Aruba AP"
        elif len(slot_devices) < self.active_connection_slots:
            return None
        else:
            status = "noMoreConnectionSlots"
            status_string = (
                "Another BLE device is already connected through this Aruba AP"
            )

        self.stats.last_active_action_status = status
        self.stats.last_active_action_error = (
            None if status == "alreadyConnected" else _format_action_error(status, status_string)
        )
        if status != "alreadyConnected":
            self.stats.active_action_failures += 1
        self._notify_listeners()
        return {
            "sent": False,
            "status": status,
            "status_string": status_string,
            "ap_mac": source,
            "action_type": request.action_type,
            "device_mac": device_mac,
        }

    async def _async_send_aruba_action_unlocked(
        self,
        *,
        ap_mac: str,
        request: ArubaBleActionRequest,
        wait_result: bool = True,
    ) -> dict[str, Any]:
        ap_mac = _normalize_mac(ap_mac) or ap_mac
        device_mac = _normalize_mac(request.device_mac) or request.device_mac
        request = request.with_action_id()
        action_started_at = monotonic()
        if request.device_mac != device_mac:
            request = ArubaBleActionRequest(
                action_type=request.action_type,
                device_mac=device_mac,
                action_id=request.action_id,
                service_uuid=request.service_uuid,
                characteristic_uuid=request.characteristic_uuid,
                value=request.value,
                timeout=request.timeout,
                apb_mac=request.apb_mac,
            )
        payload = encode_action_message(
            access_token=self.access_token,
            ap_mac=ap_mac,
            actions=[request],
        )
        future: asyncio.Future | None = None
        if wait_result:
            future = asyncio.get_running_loop().create_future()
            self._pending_actions[request.action_id or ""] = future
            self._pending_action_contexts[request.action_id or ""] = _PendingActionContext(
                ap_mac=ap_mac,
                device_mac=device_mac,
                action_type=request.action_type,
                started_at=action_started_at,
            )

        try:
            await self._receiver.async_send_to_source(ap_mac, payload)
        except Exception as err:
            context = None
            if future is not None:
                self._pending_actions.pop(request.action_id or "", None)
                context = self._pending_action_contexts.pop(request.action_id or "", None)
            self._record_active_action_duration(
                action_type=request.action_type,
                status="send_error",
                started_at=context.started_at if context is not None else action_started_at,
            )
            self.stats.active_action_send_errors += 1
            self.stats.last_active_action_error = f"{type(err).__name__}: {err}"
            self._notify_listeners()
            raise

        self.stats.active_actions_sent += 1
        self.stats.last_active_action_id = request.action_id
        self.stats.last_active_action_error = None
        self._notify_listeners()

        response: dict[str, Any] = {
            "sent": True,
            "action_id": request.action_id,
            "ap_mac": ap_mac,
            "action_type": request.action_type,
            "device_mac": device_mac,
        }
        if future is None:
            self._record_active_action_duration(
                action_type=request.action_type,
                status="sent_no_wait",
                started_at=action_started_at,
            )
            return response

        try:
            result = await asyncio.wait_for(future, timeout=request.timeout + 5)
        except asyncio.CancelledError:
            self._pending_actions.pop(request.action_id or "", None)
            context = self._pending_action_contexts.pop(request.action_id or "", None)
            future.cancel()
            self._record_active_action_duration(
                action_type=request.action_type,
                status="cancelled_waiting_for_action_result",
                started_at=context.started_at if context is not None else action_started_at,
            )
            self.stats.active_action_cancellations += 1
            self.stats.last_active_action_status = "cancelled_waiting_for_action_result"
            self.stats.last_active_action_error = "cancelled_waiting_for_action_result"
            self._notify_listeners()
            raise
        except TimeoutError:
            self._pending_actions.pop(request.action_id or "", None)
            context = self._pending_action_contexts.pop(request.action_id or "", None)
            self._record_active_action_duration(
                action_type=request.action_type,
                status="timeout_waiting_for_action_result",
                started_at=context.started_at if context is not None else action_started_at,
            )
            self.stats.active_action_timeouts += 1
            self.stats.last_active_action_status = "timeout_waiting_for_action_result"
            self.stats.last_active_action_error = "timeout_waiting_for_action_result"
            self._notify_listeners()
            response["result"] = {
                "received": False,
                "status": "timeout_waiting_for_action_result",
            }
            return response

        response["result"] = {
            "received": True,
            "status": result.status_name,
            "status_string": result.status_string,
            "device_mac": _normalize_mac(result.device_mac) or device_mac,
            "apb_mac": result.apb_mac,
        }
        return response

    async def async_gatt_write(
        self,
        *,
        ap_mac: str,
        device_mac: str,
        service_uuid: str,
        characteristic_uuid: str,
        value: bytes,
        with_response: bool = True,
        timeout: int = 20,
        wait_result: bool = True,
    ) -> dict[str, Any]:
        key = _characteristic_key(ap_mac, device_mac, service_uuid, characteristic_uuid)
        if key is None:
            raise ValueError(
                "ap_mac, device_mac, service_uuid, and characteristic_uuid are required"
            )
        async with self._active_operation(ap_mac, device_mac):
            return await self._async_send_aruba_action_unlocked(
                ap_mac=ap_mac,
                request=ArubaBleActionRequest(
                    action_type=ACTION_GATT_WRITE_WITH_RESPONSE
                    if with_response
                    else ACTION_GATT_WRITE,
                    device_mac=device_mac,
                    service_uuid=key[2],
                    characteristic_uuid=key[3],
                    value=value,
                    timeout=timeout,
                ),
                wait_result=wait_result,
            )

    async def async_gatt_notification(
        self,
        *,
        ap_mac: str,
        device_mac: str,
        service_uuid: str,
        characteristic_uuid: str,
        enable: bool,
        indicate: bool = False,
        timeout: int = 20,
        wait_result: bool = True,
    ) -> dict[str, Any]:
        key = _characteristic_key(ap_mac, device_mac, service_uuid, characteristic_uuid)
        if key is None:
            raise ValueError(
                "ap_mac, device_mac, service_uuid, and characteristic_uuid are required"
            )
        async with self._active_operation(ap_mac, device_mac):
            return await self._async_gatt_notification_unlocked(
                ap_mac=ap_mac,
                device_mac=device_mac,
                service_uuid=key[2],
                characteristic_uuid=key[3],
                enable=enable,
                indicate=indicate,
                timeout=timeout,
                wait_result=wait_result,
            )

    async def _async_gatt_notification_unlocked(
        self,
        *,
        ap_mac: str,
        device_mac: str,
        service_uuid: str,
        characteristic_uuid: str,
        enable: bool,
        indicate: bool = False,
        timeout: int = 20,
        wait_result: bool = True,
    ) -> dict[str, Any]:
        return await self._async_send_aruba_action_unlocked(
            ap_mac=ap_mac,
            request=ArubaBleActionRequest(
                action_type=ACTION_GATT_INDICATION if indicate else ACTION_GATT_NOTIFICATION,
                device_mac=device_mac,
                service_uuid=service_uuid,
                characteristic_uuid=characteristic_uuid,
                value=b"\x01" if enable else b"\x00",
                timeout=timeout,
            ),
            wait_result=wait_result,
        )

    async def async_start_gatt_notify(
        self,
        *,
        ap_mac: str,
        device_mac: str,
        service_uuid: str,
        characteristic_uuid: str,
        callback: Callable[[ArubaCharacteristic], None],
        timeout: int = 20,
    ) -> dict[str, Any]:
        key = _characteristic_key(ap_mac, device_mac, service_uuid, characteristic_uuid)
        if key is None:
            raise ValueError(
                "ap_mac, device_mac, service_uuid, and characteristic_uuid are required"
            )
        async with self._active_operation(ap_mac, device_mac):
            callbacks = self._notification_callbacks.get(key, [])
            if callback in callbacks:
                return {
                    "sent": False,
                    "status": "already_registered",
                    "source": key[0],
                    "device_mac": key[1],
                    "service_uuid": key[2],
                    "characteristic_uuid": key[3],
                }
            if callbacks:
                callbacks.append(callback)
                self.stats.active_notifications_enabled += 1
                return {
                    "sent": False,
                    "status": "already_enabled",
                    "source": key[0],
                    "device_mac": key[1],
                    "service_uuid": key[2],
                    "characteristic_uuid": key[3],
                }
            response = await self._async_gatt_notification_unlocked(
                ap_mac=ap_mac,
                device_mac=device_mac,
                service_uuid=key[2],
                characteristic_uuid=key[3],
                enable=True,
                timeout=timeout,
                wait_result=True,
            )
            result = response.get("result", {})
            if result.get("status") == "success":
                self._notification_callbacks[key] = [callback]
                self.stats.active_notifications_enabled += 1
            return response

    def register_gatt_notify_callback(
        self,
        *,
        ap_mac: str,
        device_mac: str,
        service_uuid: str,
        characteristic_uuid: str,
        callback: Callable[[ArubaCharacteristic], None],
    ) -> bool:
        key = _characteristic_key(ap_mac, device_mac, service_uuid, characteristic_uuid)
        if key is None:
            raise ValueError(
                "ap_mac, device_mac, service_uuid, and characteristic_uuid are required"
            )
        callbacks = self._notification_callbacks.setdefault(key, [])
        if callback in callbacks:
            return False
        callbacks.append(callback)
        self.stats.active_notifications_enabled += 1
        self._notify_listeners()
        return True

    async def async_stop_gatt_notify(
        self,
        *,
        ap_mac: str,
        device_mac: str,
        service_uuid: str,
        characteristic_uuid: str,
        callback: Callable[[ArubaCharacteristic], None],
        timeout: int = 20,
    ) -> dict[str, Any]:
        key = _characteristic_key(ap_mac, device_mac, service_uuid, characteristic_uuid)
        if key is None:
            raise ValueError(
                "ap_mac, device_mac, service_uuid, and characteristic_uuid are required"
            )
        async with self._active_operation(ap_mac, device_mac):
            callbacks = self._notification_callbacks.get(key, [])
            if callback not in callbacks:
                return {
                    "sent": False,
                    "status": "not_registered",
                    "source": key[0],
                    "device_mac": key[1],
                    "service_uuid": key[2],
                    "characteristic_uuid": key[3],
                }
            if len(callbacks) > 1:
                callbacks.remove(callback)
                self.stats.active_notifications_enabled = max(
                    0,
                    self.stats.active_notifications_enabled - 1,
                )
                return {
                    "sent": False,
                    "status": "callbacks_remaining",
                    "source": key[0],
                    "device_mac": key[1],
                    "service_uuid": key[2],
                    "characteristic_uuid": key[3],
                }
            response = await self._async_gatt_notification_unlocked(
                ap_mac=ap_mac,
                device_mac=device_mac,
                service_uuid=key[2],
                characteristic_uuid=key[3],
                enable=False,
                timeout=timeout,
                wait_result=True,
            )
            result = response.get("result", {})
            if result.get("status") == "success":
                callbacks.remove(callback)
                self.stats.active_notifications_enabled = max(
                    0,
                    self.stats.active_notifications_enabled - 1,
                )
                self._notification_callbacks.pop(key, None)
            return response

    def forget_gatt_notify_callback(
        self,
        *,
        ap_mac: str | None = None,
        device_mac: str,
        service_uuid: str,
        characteristic_uuid: str,
        callback: Callable[[ArubaCharacteristic], None],
    ) -> bool:
        """Remove a local notification callback without sending an Aruba action.

        This is used when the owning Bleak client has already disconnected or is
        being torn down. At that point the important invariant is that stale
        callbacks do not survive and receive future northbound characteristic
        updates for a dead client.
        """
        if ap_mac is None:
            matching_keys = [
                key
                for key, callbacks in self._notification_callbacks.items()
                if key[1:] == (
                    _normalize_mac(device_mac),
                    _normalize_uuid(service_uuid),
                    _normalize_uuid(characteristic_uuid),
                )
                and callback in callbacks
            ]
        else:
            key = _characteristic_key(ap_mac, device_mac, service_uuid, characteristic_uuid)
            matching_keys = [key] if key is not None else []

        removed = False
        for key in matching_keys:
            callbacks = self._notification_callbacks.get(key)
            if not callbacks or callback not in callbacks:
                continue

            callbacks.remove(callback)
            self.stats.active_notifications_enabled = max(
                0,
                self.stats.active_notifications_enabled - 1,
            )
            if not callbacks:
                self._notification_callbacks.pop(key, None)
            removed = True
        return removed

    def can_connect_source(self, source: str) -> bool:
        normalized = _normalize_mac(source) or source.upper()
        if normalized not in {
            _normalize_mac(connected_source) or connected_source.upper()
            for connected_source in self._receiver.connected_sources()
        }:
            return False
        return (
            len(
                {
                    *self.active_devices_for_source(normalized),
                    *self.pending_connect_devices_for_source(normalized),
                }
            )
            < self.active_connection_slots
        )

    def connection_slots_for_source(self, source: str) -> int:
        return self.active_connection_slots

    def active_devices_for_source(self, source: str) -> list[str]:
        normalized = _normalize_mac(source) or source.upper()
        return sorted(
            device_mac
            for source_mac, device_mac in self._active_device_keys_by_source.get(
                normalized, set()
            )
            if source_mac == normalized and self.is_device_active(source_mac, device_mac)
        )

    def pending_connect_devices_for_source(self, source: str) -> list[str]:
        normalized = _normalize_mac(source) or source.upper()
        return sorted(
            {
                context.device_mac
                for context in self._pending_action_contexts.values()
                if context.ap_mac == normalized
                and context.action_type == ACTION_BLE_CONNECT
            }
        )

    def characteristics_for_device(
        self,
        device_mac: str,
        *,
        source: str | None = None,
    ) -> list[ArubaCharacteristic]:
        normalized = _normalize_mac(device_mac)
        normalized_source = _normalize_mac(source) if source is not None else None
        return [
            characteristic
            for (
                known_source,
                known_device,
                _,
                _,
            ), characteristic in self._last_characteristics.items()
            if known_device == normalized
            and (normalized_source is None or known_source == normalized_source)
        ]

    def service_uuids_for_device(self, device_mac: str) -> set[str]:
        normalized = _normalize_mac(device_mac)
        if normalized is None:
            return set()
        return set(self._device_advertised_service_uuids.get(normalized, set()))

    def _record_active_action_duration(
        self,
        *,
        action_type: str,
        status: str,
        started_at: float,
    ) -> None:
        duration_ms = max(0, round((monotonic() - started_at) * 1000))
        self.stats.last_active_action_type = action_type
        self.stats.last_active_action_duration_ms = duration_ms
        self.stats.active_action_duration_total_ms += duration_ms
        if (
            self.stats.slowest_active_action_duration_ms is None
            or duration_ms > self.stats.slowest_active_action_duration_ms
        ):
            self.stats.slowest_active_action_duration_ms = duration_ms
            self.stats.slowest_active_action_type = action_type
            self.stats.slowest_active_action_status = status

    def _record_characteristic_wait_duration(
        self,
        *,
        status: str,
        started_at: float,
    ) -> None:
        duration_ms = max(0, round((monotonic() - started_at) * 1000))
        self.stats.last_active_characteristic_wait_status = status
        self.stats.last_active_characteristic_wait_duration_ms = duration_ms
        self.stats.active_characteristic_wait_duration_total_ms += duration_ms
        if (
            self.stats.slowest_active_characteristic_wait_duration_ms is None
            or duration_ms > self.stats.slowest_active_characteristic_wait_duration_ms
        ):
            self.stats.slowest_active_characteristic_wait_duration_ms = duration_ms
            self.stats.slowest_active_characteristic_wait_status = status

    async def async_wait_for_device_characteristics(
        self,
        device_mac: str,
        *,
        source: str | None = None,
        timeout: float = 3.0,
    ) -> list[ArubaCharacteristic]:
        started_at = monotonic()
        existing = self.characteristics_for_device(device_mac, source=source)
        if existing:
            self._record_characteristic_wait_duration(
                status="cached",
                started_at=started_at,
            )
            return existing

        normalized = _normalize_mac(device_mac)
        normalized_source = _normalize_mac(source) if source is not None else None
        future = asyncio.get_running_loop().create_future()
        discovery_key = (normalized_source, normalized)
        self._pending_device_characteristics.setdefault(discovery_key, []).append(future)
        self.stats.active_characteristic_waits += 1
        try:
            characteristics = await asyncio.wait_for(future, timeout=timeout)
            self._record_characteristic_wait_duration(
                status="received",
                started_at=started_at,
            )
            return characteristics
        except TimeoutError:
            self.stats.active_characteristic_wait_timeouts += 1
            self._record_characteristic_wait_duration(
                status="timeout",
                started_at=started_at,
            )
            return []
        finally:
            waiters = self._pending_device_characteristics.get(discovery_key)
            if waiters is not None and future in waiters:
                waiters.remove(future)
                if not waiters:
                    self._pending_device_characteristics.pop(discovery_key, None)

    async def async_gatt_read(
        self,
        *,
        ap_mac: str,
        device_mac: str,
        service_uuid: str,
        characteristic_uuid: str,
        timeout: int = 20,
        wait_result: bool = True,
    ) -> dict[str, Any]:
        key = _characteristic_key(ap_mac, device_mac, service_uuid, characteristic_uuid)
        if key is None:
            raise ValueError(
                "ap_mac, device_mac, service_uuid, and characteristic_uuid are required"
            )
        async with self._active_operation(ap_mac, device_mac):
            return await self._async_gatt_read_unlocked(
                ap_mac=ap_mac,
                device_mac=device_mac,
                service_uuid=key[2],
                characteristic_uuid=key[3],
                timeout=timeout,
                wait_result=wait_result,
                key=key,
            )

    async def _async_gatt_read_unlocked(
        self,
        *,
        ap_mac: str,
        device_mac: str,
        service_uuid: str,
        characteristic_uuid: str,
        timeout: int,
        wait_result: bool,
        key: tuple[str, str, str, str],
    ) -> dict[str, Any]:
        characteristic_future = asyncio.get_running_loop().create_future()
        if wait_result:
            self._pending_characteristics.setdefault(key, []).append(characteristic_future)
        try:
            response = await self._async_send_aruba_action_unlocked(
                ap_mac=ap_mac,
                request=ArubaBleActionRequest(
                    action_type=ACTION_GATT_READ,
                    device_mac=device_mac,
                    service_uuid=service_uuid,
                    characteristic_uuid=characteristic_uuid,
                    timeout=timeout,
                ),
                wait_result=wait_result,
            )
            if not wait_result:
                return response
            action_result = response.get("result")
            if action_result is not None and action_result.get("status") != "success":
                return response
            try:
                characteristic = await asyncio.wait_for(
                    characteristic_future,
                    timeout=timeout + 5,
                )
            except TimeoutError:
                response["characteristic"] = {
                    "received": False,
                    "status": "timeout_waiting_for_characteristic",
                }
            except _CharacteristicWaitFailed as err:
                response["characteristic"] = {
                    "received": False,
                    "status": err.status,
                    "status_string": err.status_string,
                }
            else:
                response["characteristic"] = {
                    "received": True,
                    "device_mac": characteristic.device_mac,
                    "service_uuid": characteristic.service_uuid,
                    "characteristic_uuid": characteristic.characteristic_uuid,
                    "value": characteristic.value.hex(),
                    "description": characteristic.description,
                    "properties": list(characteristic.properties),
                }
            return response
        finally:
            waiters = self._pending_characteristics.get(key)
            if waiters is not None and characteristic_future in waiters:
                waiters.remove(characteristic_future)
                if not waiters:
                    self._pending_characteristics.pop(key, None)
            if characteristic_future.done() and not characteristic_future.cancelled():
                characteristic_future.exception()
            if not characteristic_future.done():
                characteristic_future.cancel()

    @asynccontextmanager
    async def _active_operation(self, ap_mac: str, device_mac: str):
        key = _source_operation_key(ap_mac)
        slot = self._active_operation_slots.get(key)
        if slot is None:
            slot = _ActiveOperationSlot()
            self._active_operation_slots[key] = slot
        slot.users += 1
        try:
            async with slot.lock:
                yield
        finally:
            slot.users = max(0, slot.users - 1)
            if slot.users == 0 and self._active_operation_slots.get(key) is slot:
                self._active_operation_slots.pop(key, None)

    def _update_stats(self, event: ArubaBleEvent) -> None:
        self.stats.events += 1
        source = _normalize_mac(event.source) or event.source.upper()
        address = _normalize_mac(event.address) or event.address.upper()
        self.stats.addresses.add(address)
        self.stats.sources.add(source)
        self.stats.service_data.update(event.advertisement.service_data)
        self.stats.manufacturer_ids.update(event.advertisement.manufacturer_data)
        if event.advertisement.local_name:
            self.stats.local_names.add(event.advertisement.local_name)
        self.stats.last_seen = datetime.now(UTC).isoformat()
        self.stats.last_address = address
        self.stats.last_source = source
        self.stats.last_rssi = event.rssi
        self.stats.last_local_name = event.advertisement.local_name
        self.stats.last_service_data = sorted(event.advertisement.service_data)
        self.stats.last_manufacturer_ids = sorted(event.advertisement.manufacturer_data)
        advertised_service_uuids = {
            _normalize_uuid(service_uuid)
            for service_uuid in (
                *event.advertisement.service_uuids,
                *event.advertisement.service_data,
            )
            if service_uuid
        }
        if advertised_service_uuids:
            self._device_advertised_service_uuids.setdefault(address, set()).update(
                advertised_service_uuids
            )

    def diagnostic_attributes(self) -> dict[str, Any]:
        receiver_stats = self._receiver.stats
        attributes = self.stats.as_dict()
        attributes.update(
            {
                "listen_host": self.host,
                "listen_port": self.port,
                "active_ble_enabled": self.enable_active_ble,
                "active_connection_slots_per_ap": self.active_connection_slots,
                "registered_scanners": len(self._remote_scanners),
                "registered_scanner_sources": sorted(self._remote_scanners),
                "receiver_connected_sources": self._receiver.connected_sources(),
                "receiver_connections_opened": receiver_stats.connections_opened,
                "receiver_connections_closed": receiver_stats.connections_closed,
                "receiver_binary_messages": receiver_stats.binary_messages,
                "receiver_text_messages": receiver_stats.text_messages,
                "receiver_invalid_tokens": receiver_stats.invalid_tokens,
                "receiver_decode_errors": receiver_stats.decode_errors,
                "receiver_last_peer": receiver_stats.last_peer,
                "receiver_running": self._task is not None and not self._task.done(),
                "active_operation_locks": len(self._active_operation_slots),
                "active_operations_in_flight": sum(
                    1 for slot in self._active_operation_slots.values() if slot.lock.locked()
                ),
                "active_operations_waiting": sum(
                    max(0, slot.users - 1)
                    for slot in self._active_operation_slots.values()
                ),
                "active_connected_devices": _format_device_keys(
                    key
                    for source_devices in self._active_device_keys_by_source.values()
                    for key in source_devices
                ),
                "active_disconnected_devices": [
                    {
                        "source": source,
                        "device_mac": device_mac,
                        "status": status,
                    }
                    for (source, device_mac), status in sorted(
                        self._device_connection_statuses.items()
                    )
                    if status in DISCONNECTED_DEVICE_STATUSES
                ],
                "active_device_mtu": [
                    {
                        "source": source,
                        "device_mac": device_mac,
                        "mtu": mtu,
                    }
                    for (source, device_mac), mtu in sorted(self._device_mtu.items())
                ],
                "active_pending_actions": [
                    {
                        "action_id": action_id,
                        "source": context.ap_mac,
                        "device_mac": context.device_mac,
                        "action_type": context.action_type,
                    }
                    for action_id, context in sorted(self._pending_action_contexts.items())
                ],
                "active_pending_characteristic_reads": [
                    {
                        "source": source,
                        "device_mac": device_mac,
                        "service_uuid": service_uuid,
                        "characteristic_uuid": characteristic_uuid,
                        "waiters": len(waiters),
                    }
                    for (
                        source,
                        device_mac,
                        service_uuid,
                        characteristic_uuid,
                    ), waiters in sorted(self._pending_characteristics.items())
                ],
                "active_pending_device_discoveries": [
                    {
                        "source": source,
                        "device_mac": device_mac,
                        "waiters": len(waiters),
                    }
                    for (source, device_mac), waiters in sorted(
                        self._pending_device_characteristics.items()
                    )
                ],
                "active_notification_subscriptions": [
                    {
                        "source": source,
                        "device_mac": device_mac,
                        "service_uuid": service_uuid,
                        "characteristic_uuid": characteristic_uuid,
                        "callbacks": len(callbacks),
                    }
                    for (
                        source,
                        device_mac,
                        service_uuid,
                        characteristic_uuid,
                    ), callbacks in sorted(self._notification_callbacks.items())
                ],
            }
        )
        return attributes

    def _notify_listeners(self) -> None:
        for listener in list(self._listeners):
            listener()

    def _notify_passive_listeners(self) -> None:
        now = monotonic()
        if now - self._last_passive_listener_update < PASSIVE_SENSOR_UPDATE_INTERVAL:
            return
        self._last_passive_listener_update = now
        self._notify_listeners()

    async def _async_forward_to_remote_scanner(self, payload: BluetoothPayload) -> bool:
        if self._register_scanner is None:
            return False

        source = _normalize_mac(payload.source) or payload.source.upper()
        try:
            scanner = self._remote_scanners.get(source)
            if scanner is None:
                scanner = await self._async_create_remote_scanner(source)
            scanner.async_on_payload(payload)
        except Exception as err:
            self.stats.bluetooth_forward_errors += 1
            self.stats.last_bluetooth_error = f"{type(err).__name__}: {err}"
            _LOGGER.exception("Failed to forward Aruba BLE advertisement through scanner")
            return False
        else:
            self.stats.bluetooth_forwards += 1
            self.stats.last_bluetooth_error = None
            return True

    async def _async_create_remote_scanner(self, source: str) -> Any:
        return self._create_remote_scanner(
            source,
            source_config_entry_id=await self._async_source_config_entry_id(source),
        )

    async def _async_source_config_entry_id(self, source: str) -> str | None:
        if self.hass is None or self._entry_id is None:
            return self._entry_id

        current = self._source_entry_ids.get(source)
        if current is not None and _config_entry_exists(self.hass, current):
            return current

        if entry := _find_ap_source_entry(self.hass, self._entry_id, source):
            self._source_entry_ids[source] = entry.entry_id
            return entry.entry_id

        flow = getattr(getattr(self.hass.config_entries, "flow", None), "async_init", None)
        if flow is None:
            return self._entry_id

        try:
            from homeassistant import config_entries

            discovery_source = config_entries.SOURCE_INTEGRATION_DISCOVERY
        except Exception:
            discovery_source = "integration_discovery"

        await flow(
            DOMAIN,
            context={"source": discovery_source},
            data={
                CONF_ENTRY_TYPE: ENTRY_TYPE_AP_SOURCE,
                CONF_AP_SOURCE: source,
                CONF_PARENT_ENTRY_ID: self._entry_id,
            },
        )
        if entry := _find_ap_source_entry(self.hass, self._entry_id, source):
            self._source_entry_ids[source] = entry.entry_id
            return entry.entry_id
        return self._entry_id

    def _create_remote_scanner(
        self,
        source: str,
        *,
        source_config_entry_id: str | None = None,
    ) -> Any:
        from .scanner import ArubaBleRemoteScanner

        if self._register_scanner is None:
            raise RuntimeError("Bluetooth scanner registration is not available")

        remote_scanner = ArubaBleRemoteScanner(
            source,
            runtime=self,
            connectable=self.enable_active_ble,
        )
        unsubs = [
            self._register_scanner(
                self.hass,
                remote_scanner.scanner,
                connection_slots=(
                    self.active_connection_slots if remote_scanner.connectable else 0
                ),
                source_domain=DOMAIN,
                source_config_entry_id=source_config_entry_id,
            ),
            remote_scanner.async_setup(),
        ]
        self._remote_scanners[source] = remote_scanner
        self._scanner_unsubs[source] = unsubs
        self.stats.active_connectable_scanners = sum(
            1 for scanner in self._remote_scanners.values() if scanner.connectable
        )
        _LOGGER.info(
            "Registered Aruba AP %s as %s Bluetooth scanner",
            source,
            "connectable" if remote_scanner.connectable else "passive",
        )
        return remote_scanner

    def _unregister_scanners(self) -> None:
        for callbacks in list(self._scanner_unsubs.values()):
            for unsubscribe in callbacks:
                unsubscribe()
        self._scanner_unsubs.clear()
        self._remote_scanners.clear()
        self.stats.active_connectable_scanners = 0

    def _async_forward_to_bluetooth(self, payload: BluetoothPayload) -> None:
        if self._bluetooth_callback is None:
            return

        try:
            self._bluetooth_callback(_payload_to_ha_service_info(payload))
        except Exception as err:
            self.stats.bluetooth_forward_errors += 1
            self.stats.last_bluetooth_error = f"{type(err).__name__}: {err}"
            _LOGGER.exception("Failed to forward Aruba BLE advertisement to Home Assistant")
        else:
            self.stats.bluetooth_forwards += 1
            self.stats.last_bluetooth_error = None


def _payload_to_ha_service_info(payload: BluetoothPayload) -> Any:
    from bleak.backends.device import BLEDevice
    from bleak.backends.scanner import AdvertisementData
    from homeassistant.components import bluetooth

    advertisement = AdvertisementData(
        local_name=payload.name,
        manufacturer_data=payload.manufacturer_data,
        service_data=payload.service_data,
        service_uuids=payload.service_uuids,
        tx_power=payload.tx_power,
        rssi=payload.rssi,
        platform_data=(),
    )
    device = BLEDevice(payload.address, payload.name, details={}, rssi=payload.rssi)
    kwargs = {
        "name": payload.name,
        "address": payload.address,
        "rssi": payload.rssi,
        "manufacturer_data": payload.manufacturer_data,
        "service_data": payload.service_data,
        "service_uuids": payload.service_uuids,
        "source": payload.source,
        "device": device,
        "advertisement": advertisement,
        "connectable": payload.connectable,
        "time": payload.time,
        "tx_power": payload.tx_power,
    }
    try:
        return bluetooth.BluetoothServiceInfoBleak(**kwargs, raw=payload.raw)
    except TypeError:
        return bluetooth.BluetoothServiceInfoBleak(**kwargs)


def _characteristic_key(
    source: str | None,
    device_mac: str | None,
    service_uuid: str | None,
    characteristic_uuid: str | None,
) -> tuple[str, str, str, str] | None:
    if not source or not device_mac or not service_uuid or not characteristic_uuid:
        return None
    normalized_source = _normalize_mac(source)
    normalized_device = _normalize_mac(device_mac)
    if normalized_source is None or normalized_device is None:
        return None
    return (
        normalized_source,
        normalized_device,
        _normalize_uuid(service_uuid),
        _normalize_uuid(characteristic_uuid),
    )


def _format_action_error(status: str | None, status_string: str | None) -> str:
    if status_string:
        return f"{status}: {status_string}"
    return str(status)


def _is_successful_action_result(
    result: ArubaActionResult,
    context: _PendingActionContext | None,
) -> bool:
    action_type = result.action_type or (context.action_type if context else None)
    if action_type == ACTION_BLE_CONNECT:
        return result.status_name in CONNECT_SUCCESS_STATUSES
    if action_type == ACTION_BLE_DISCONNECT:
        return result.status_name in DISCONNECT_SUCCESS_STATUSES
    return result.status_name == "success"


def _device_key(source: str, device_mac: str) -> tuple[str, str]:
    return (
        _normalize_mac(source) or source.upper(),
        _normalize_mac(device_mac) or device_mac.upper(),
    )


def _source_operation_key(source: str) -> tuple[str, str]:
    return (_normalize_mac(source) or source.upper(), "*")


def _config_entry_exists(hass: Any, entry_id: str) -> bool:
    getter = getattr(hass.config_entries, "async_get_entry", None)
    if getter is None:
        return False
    return getter(entry_id) is not None


def _find_ap_source_entry(hass: Any, parent_entry_id: str, source: str) -> Any | None:
    entries_getter = getattr(hass.config_entries, "async_entries", None)
    if entries_getter is None:
        return None
    normalized = _normalize_mac(source) or source.upper()
    for entry in entries_getter(DOMAIN):
        data = getattr(entry, "data", {})
        if data.get(CONF_ENTRY_TYPE) != ENTRY_TYPE_AP_SOURCE:
            continue
        if data.get(CONF_PARENT_ENTRY_ID) != parent_entry_id:
            continue
        entry_source = _normalize_mac(data.get(CONF_AP_SOURCE)) or str(
            data.get(CONF_AP_SOURCE, "")
        ).upper()
        if entry_source == normalized:
            return entry
    return None


def _normalize_mac(value: str | None) -> str | None:
    if value is None:
        return None
    text = value.strip()
    if not text:
        return None
    compact = text.replace(":", "").replace("-", "").replace(".", "")
    if len(compact) == 12:
        try:
            int(compact, 16)
        except ValueError:
            pass
        else:
            compact = compact.upper()
            return ":".join(compact[index : index + 2] for index in range(0, 12, 2))
    return text.upper()


def _normalize_uuid(value: str) -> str:
    text = str(value).strip().lower()
    compact = text.replace("-", "")
    if len(compact) == 4:
        return f"0000{compact}-0000-1000-8000-00805f9b34fb"
    if len(compact) == 32:
        return (
            f"{compact[0:8]}-{compact[8:12]}-{compact[12:16]}-"
            f"{compact[16:20]}-{compact[20:32]}"
        )
    return text


def _format_device_keys(keys) -> list[dict[str, str]]:
    return [
        {
            "source": source,
            "device_mac": device_mac,
        }
        for source, device_mac in sorted(keys)
    ]
