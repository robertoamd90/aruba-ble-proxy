from __future__ import annotations

import asyncio
import inspect
import logging
from time import monotonic
from typing import Any

from .active import (
    ACTION_BLE_CONNECT,
    ACTION_BLE_DISCONNECT,
    ArubaBleActionRequest,
)
from .models import ArubaCharacteristic


ARUBA_TO_BLEAK_PROPERTIES = {
    "broadcast": "broadcast",
    "read": "read",
    "writeWithoutResponse": "write-without-response",
    "writeWithResponse": "write",
    "notify": "notify",
    "indicate": "indicate",
    "signedWrite": "authenticated-signed-writes",
    "writeReliable": "reliable-write",
    "writeAux": "writable-auxiliaries",
}

LOCAL_SUCCESS_STATUSES = {
    "already_registered",
    "already_enabled",
    "callbacks_remaining",
}
CONNECT_SUCCESS_STATUSES = {"alreadyConnected"}
DISCONNECT_SUCCESS_STATUSES = {
    "notConnected",
    "deviceDisconnected",
    "inactivityTimeout",
    "sourceDisconnected",
}
STOP_NOTIFY_SUCCESS_STATUSES = {"not_registered"}

SWITCHBOT_ADV_SERVICE_UUID = "0000fd3d-0000-1000-8000-00805f9b34fb"
SWITCHBOT_COMMAND_SERVICE_UUID = "cba20d00-224d-11e6-9fb8-0002a5d5c51b"
SWITCHBOT_WRITE_CHAR_UUID = "cba20002-224d-11e6-9fb8-0002a5d5c51b"
SWITCHBOT_READ_CHAR_UUID = "cba20003-224d-11e6-9fb8-0002a5d5c51b"

LOGGER = logging.getLogger(__name__)


def create_aruba_bleak_client(runtime: Any, source: str):
    """Create a Bleak backend class bound to one Aruba AP source."""

    from bleak.backends.client import BaseBleakClient
    from bleak.backends.service import BleakGATTServiceCollection
    from bleak.exc import BleakError

    session_slots = max(1, int(getattr(runtime, "active_connection_slots", 1)))
    session_semaphore = asyncio.Semaphore(session_slots)

    class ArubaBleakClient(BaseBleakClient):
        def __init__(self, address_or_ble_device, **kwargs):
            kwargs.setdefault("timeout", 10.0)
            super().__init__(address_or_ble_device, **kwargs)
            normalized_address = _ble_device_address(
                getattr(self, "address", None)
            ) or _ble_device_address(address_or_ble_device)
            if normalized_address is not None:
                self.address = normalized_address
            self._runtime = runtime
            self._source = source
            self._is_connected = False
            self._notify_callbacks = {}
            self._local_notify_callbacks = set()
            self._disconnect_listener_unsub = None
            self._disconnect_requested = False
            self._session_slot_acquired = False
            self.services = BleakGATTServiceCollection()

        @property
        def name(self) -> str:
            return str(self.address)

        @property
        def mtu_size(self) -> int:
            mtu_for_device = getattr(self._runtime, "mtu_for_device", None)
            if mtu_for_device is None:
                return 23
            return int(mtu_for_device(self._source, self.address) or 23)

        @property
        def is_connected(self) -> bool:
            self._sync_disconnected_from_runtime()
            return self._is_connected

        async def connect(self, pair: bool = False, **kwargs: Any) -> bool:
            self._sync_disconnected_from_runtime()
            if self._is_connected:
                return True
            if pair:
                raise BleakError("Aruba BLE pairing is not implemented yet")
            await self._acquire_session_slot()
            timeout = int(kwargs.get("timeout", self._timeout))
            try:
                response = await self._runtime.async_send_aruba_action(
                    ap_mac=self._source,
                    request=ArubaBleActionRequest(
                        action_type=ACTION_BLE_CONNECT,
                        device_mac=self.address,
                        timeout=timeout,
                    ),
                    wait_result=True,
                )
            except asyncio.CancelledError:
                self._release_session_slot()
                raise
            except Exception:
                self._release_session_slot()
                raise
            try:
                _raise_for_failed_action(
                    response,
                    BleakError,
                    allow_statuses=CONNECT_SUCCESS_STATUSES,
                )
            except Exception:
                try:
                    await self._send_best_effort_disconnect()
                finally:
                    self._release_session_slot()
                raise
            self._is_connected = True
            self._register_disconnect_listener()
            try:
                advertisement_service_uuids = self._advertisement_service_uuids()
                if _service_collection_has_characteristics(self.services):
                    return True
                advertised_services = build_service_collection(
                    [],
                    advertisement_service_uuids=advertisement_service_uuids,
                )
                if _service_collection_has_characteristics(advertised_services):
                    self.services = advertised_services
                    return True
                characteristics = await _call_wait_for_device_characteristics(
                    self._runtime,
                    self.address,
                    source=self._source,
                )
                if not self.is_connected:
                    raise BleakError("Aruba BLE client disconnected during service discovery")
                self.services = build_service_collection(
                    characteristics,
                    advertisement_service_uuids=advertisement_service_uuids,
                )
                return True
            except asyncio.CancelledError:
                await self._cleanup_failed_connect()
                raise
            except Exception:
                await self._cleanup_failed_connect()
                raise

        async def disconnect(self) -> bool:
            self._sync_disconnected_from_runtime()
            if not self._is_connected:
                self._mark_disconnected(notify=False)
                return True
            self._disconnect_requested = True
            try:
                response = await self._runtime.async_send_aruba_action(
                    ap_mac=self._source,
                    request=ArubaBleActionRequest(
                        action_type=ACTION_BLE_DISCONNECT,
                        device_mac=self.address,
                        timeout=20,
                    ),
                    wait_result=True,
                )
                _raise_for_failed_action(
                    response,
                    BleakError,
                    allow_statuses=DISCONNECT_SUCCESS_STATUSES,
                )
                self._mark_disconnected(notify=False)
            except asyncio.CancelledError:
                self._mark_disconnected(notify=False)
                raise
            except Exception:
                self._mark_disconnected(notify=False)
                raise
            finally:
                self._disconnect_requested = False
            return True

        async def pair(self, *args: Any, **kwargs: Any) -> None:
            raise BleakError("Aruba BLE pairing is not implemented yet")

        async def unpair(self) -> None:
            raise BleakError("Aruba BLE unpairing is not implemented yet")

        async def read_gatt_char(
            self,
            characteristic,
            *,
            use_cached: bool = False,
            **kwargs: Any,
        ) -> bytearray:
            self._ensure_connected(BleakError)
            characteristic = self._resolve_characteristic(characteristic, BleakError)
            service_uuid = _normalize_uuid(characteristic.service_uuid)
            characteristic_uuid = _normalize_uuid(characteristic.uuid)
            response = await self._runtime.async_gatt_read(
                ap_mac=self._source,
                device_mac=self.address,
                service_uuid=service_uuid,
                characteristic_uuid=characteristic_uuid,
                timeout=int(kwargs.get("timeout", self._timeout)),
                wait_result=True,
            )
            _raise_for_failed_action(response, BleakError)
            characteristic_result = response.get("characteristic", {})
            value = characteristic_result.get("value")
            if value is None:
                detail = _status_detail(
                    characteristic_result.get("status"),
                    characteristic_result.get("status_string"),
                )
                raise BleakError(
                    "Aruba GATT read did not return a characteristic value"
                    + (f": {detail}" if detail else "")
                )
            return bytearray.fromhex(value)

        async def read_gatt_descriptor(
            self,
            descriptor,
            *,
            use_cached: bool = False,
            **kwargs: Any,
        ) -> bytearray:
            raise BleakError("Aruba GATT descriptor read is not implemented yet")

        async def write_gatt_char(
            self,
            characteristic,
            data,
            response: bool | None = None,
            **kwargs: Any,
        ) -> None:
            self._ensure_connected(BleakError)
            characteristic = self._resolve_characteristic(characteristic, BleakError)
            service_uuid = _normalize_uuid(characteristic.service_uuid)
            characteristic_uuid = _normalize_uuid(characteristic.uuid)
            if response is None:
                response = _write_with_response_from_characteristic(characteristic)
            action_response = await self._runtime.async_gatt_write(
                ap_mac=self._source,
                device_mac=self.address,
                service_uuid=service_uuid,
                characteristic_uuid=characteristic_uuid,
                value=bytes(data),
                with_response=response,
                timeout=int(kwargs.get("timeout", 20)),
                wait_result=bool(response),
            )
            _raise_for_failed_action(action_response, BleakError)

        async def write_gatt_descriptor(self, descriptor, data) -> None:
            raise BleakError("Aruba GATT descriptor write is not implemented yet")

        async def start_notify(self, characteristic, callback, **kwargs: Any) -> None:
            self._ensure_connected(BleakError)
            characteristic = self._resolve_characteristic(characteristic, BleakError)
            service_uuid = _normalize_uuid(characteristic.service_uuid)
            characteristic_uuid = _normalize_uuid(characteristic.uuid)
            if characteristic_uuid in self._notify_callbacks:
                raise BleakError(
                    "Aruba GATT notification callback is already registered "
                    f"for {characteristic_uuid}"
                )

            dispatch = _make_notify_dispatcher(callback)

            def _notification_callback(update: ArubaCharacteristic) -> None:
                value = bytearray(update.value)
                if not value:
                    return
                result = dispatch(characteristic, value)
                if inspect.isawaitable(result):
                    self._schedule_notify_callback(result)

            response = await self._runtime.async_start_gatt_notify(
                ap_mac=self._source,
                device_mac=self.address,
                service_uuid=service_uuid,
                characteristic_uuid=characteristic_uuid,
                callback=_notification_callback,
                timeout=int(kwargs.get("timeout", 20)),
            )
            try:
                _raise_for_failed_action(response, BleakError)
            except BleakError:
                if (
                    _is_local_fallback_characteristic(characteristic)
                    and _response_status(response) == "characteristicNotFound"
                ):
                    self._register_runtime_notify_callback(
                        service_uuid,
                        characteristic_uuid,
                        _notification_callback,
                    )
                    self._notify_callbacks[characteristic_uuid] = (
                        service_uuid,
                        _notification_callback,
                    )
                    self._local_notify_callbacks.add(characteristic_uuid)
                    return
                raise
            if not self.is_connected:
                self._forget_runtime_notify_callback(
                    service_uuid,
                    characteristic_uuid,
                    _notification_callback,
                )
                raise BleakError("Aruba BLE client disconnected while enabling notifications")
            self._notify_callbacks[characteristic_uuid] = (
                service_uuid,
                _notification_callback,
            )

        async def stop_notify(self, characteristic, **kwargs: Any) -> None:
            self._ensure_connected(BleakError)
            characteristic = self._resolve_characteristic(characteristic, BleakError)
            characteristic_uuid = _normalize_uuid(characteristic.uuid)
            registered = self._notify_callbacks.get(characteristic_uuid)
            if registered is None:
                raise BleakError("Aruba GATT notification callback was not registered")
            service_uuid, callback = registered
            if characteristic_uuid in self._local_notify_callbacks:
                self._forget_runtime_notify_callback(
                    service_uuid,
                    characteristic_uuid,
                    callback,
                )
                self._notify_callbacks.pop(characteristic_uuid, None)
                self._local_notify_callbacks.discard(characteristic_uuid)
                return
            response = await self._runtime.async_stop_gatt_notify(
                ap_mac=self._source,
                device_mac=self.address,
                service_uuid=service_uuid,
                characteristic_uuid=characteristic_uuid,
                callback=callback,
                timeout=int(kwargs.get("timeout", 20)),
            )
            _raise_for_failed_action(
                response,
                BleakError,
                allow_statuses=STOP_NOTIFY_SUCCESS_STATUSES,
            )
            self._notify_callbacks.pop(characteristic_uuid, None)

        async def get_services(self, **kwargs: Any):
            self._ensure_connected(BleakError)
            return self.services

        def set_cached_services(self, services) -> None:
            if services is not None:
                self.services = services

        async def clear_cache(self) -> bool:
            self.services = BleakGATTServiceCollection()
            clear_runtime_cache = getattr(
                self._runtime,
                "clear_device_characteristics",
                None,
            )
            if clear_runtime_cache is not None:
                try:
                    clear_runtime_cache(self._source, self.address)
                except Exception:
                    LOGGER.exception(
                        "Failed to clear Aruba BLE runtime characteristic cache for %s",
                        self.address,
                    )
            return True

        async def set_connection_params(
            self,
            min_interval: int,
            max_interval: int,
            latency: int,
            timeout: int,
        ) -> None:
            return None

        def set_disconnected_callback(self, callback, **kwargs: Any) -> None:
            self._disconnected_callback = callback

        def _forget_local_notify_callbacks(self) -> None:
            for characteristic_uuid, (service_uuid, callback) in list(
                self._notify_callbacks.items()
            ):
                self._forget_runtime_notify_callback(
                    service_uuid,
                    characteristic_uuid,
                    callback,
                )
            self._notify_callbacks.clear()
            self._local_notify_callbacks.clear()

        def _register_runtime_notify_callback(
            self,
            service_uuid: str,
            characteristic_uuid: str,
            callback: Any,
        ) -> None:
            register_callback = getattr(self._runtime, "register_gatt_notify_callback")
            register_callback(
                ap_mac=self._source,
                device_mac=self.address,
                service_uuid=service_uuid,
                characteristic_uuid=characteristic_uuid,
                callback=callback,
            )

        def _forget_runtime_notify_callback(
            self,
            service_uuid: str,
            characteristic_uuid: str,
            callback: Any,
        ) -> None:
            forget_callback = getattr(self._runtime, "forget_gatt_notify_callback", None)
            if forget_callback is None:
                return
            try:
                forget_callback(
                    ap_mac=self._source,
                    device_mac=self.address,
                    service_uuid=service_uuid,
                    characteristic_uuid=characteristic_uuid,
                    callback=callback,
                )
            except Exception:
                LOGGER.exception(
                    "Failed to forget Aruba BLE notification callback for %s",
                    characteristic_uuid,
                )

        def _register_disconnect_listener(self) -> None:
            self._unregister_disconnect_listener()
            add_listener = getattr(self._runtime, "add_device_disconnect_listener", None)
            if add_listener is None:
                return
            self._disconnect_listener_unsub = add_listener(
                self._source,
                self.address,
                self._handle_runtime_disconnect,
            )

        def _unregister_disconnect_listener(self) -> None:
            if self._disconnect_listener_unsub is None:
                return
            self._disconnect_listener_unsub()
            self._disconnect_listener_unsub = None

        def _handle_runtime_disconnect(self, status: Any) -> None:
            self._mark_disconnected(notify=not self._disconnect_requested)

        def _runtime_reports_connected(self) -> bool:
            is_device_active = getattr(self._runtime, "is_device_active", None)
            if is_device_active is None:
                return True
            return bool(is_device_active(self._source, self.address))

        def _sync_disconnected_from_runtime(self) -> bool:
            if self._is_connected and not self._runtime_reports_connected():
                self._mark_disconnected(notify=True)
                return True
            return False

        def _ensure_connected(self, error_cls) -> None:
            self._sync_disconnected_from_runtime()
            if not self._is_connected:
                raise error_cls("Aruba BLE client is not connected")

        def _resolve_characteristic(self, characteristic, error_cls):
            if _is_resolved_characteristic(characteristic):
                return characteristic

            get_characteristic = getattr(self.services, "get_characteristic", None)
            if get_characteristic is not None:
                specifiers = [characteristic]
                if isinstance(characteristic, str):
                    normalized = _normalize_uuid(characteristic)
                    if normalized != characteristic:
                        specifiers.append(normalized)

                for specifier in specifiers:
                    resolved = get_characteristic(specifier)
                    if _is_resolved_characteristic(resolved):
                        return resolved

            raise error_cls(f"Aruba GATT characteristic not found: {characteristic}")

        def _advertisement_service_uuids(self) -> set[str]:
            getter = getattr(self._runtime, "service_uuids_for_device", None)
            if getter is None:
                return set()
            return {
                _normalize_uuid(service_uuid)
                for service_uuid in getter(self.address)
                if service_uuid
            }

        def _schedule_notify_callback(self, result) -> None:
            task = asyncio.create_task(result)
            task.add_done_callback(_log_notify_callback_task_result)

        async def _cleanup_failed_connect(self) -> None:
            if self._is_connected and self._runtime_reports_connected():
                await self._send_best_effort_disconnect()
            self._mark_disconnected(notify=False)

        async def _send_best_effort_disconnect(self) -> None:
            try:
                await self._runtime.async_send_aruba_action(
                    ap_mac=self._source,
                    request=ArubaBleActionRequest(
                        action_type=ACTION_BLE_DISCONNECT,
                        device_mac=self.address,
                        timeout=5,
                    ),
                    wait_result=False,
                )
            except Exception:
                pass

        async def _acquire_session_slot(self) -> None:
            if self._session_slot_acquired:
                return
            started_at = monotonic()
            await session_semaphore.acquire()
            self._session_slot_acquired = True
            waited_ms = max(0, round((monotonic() - started_at) * 1000))
            if waited_ms:
                LOGGER.debug(
                    "Waited %sms for Aruba BLE session slot on %s",
                    waited_ms,
                    self._source,
                )

        def _release_session_slot(self) -> None:
            if not self._session_slot_acquired:
                return
            self._session_slot_acquired = False
            session_semaphore.release()

        def _mark_disconnected(self, *, notify: bool) -> None:
            if not self._is_connected and not self._notify_callbacks:
                self._unregister_disconnect_listener()
                self._release_session_slot()
                return
            self._is_connected = False
            self._forget_local_notify_callbacks()
            self._unregister_disconnect_listener()
            self._release_session_slot()
            if notify:
                self._call_disconnected_callback()

        def _call_disconnected_callback(self) -> None:
            callback = getattr(self, "_disconnected_callback", None)
            if callback is None:
                return
            result = _call_compatible_callback(callback, ((self,), ()))
            if inspect.isawaitable(result):
                self._schedule_notify_callback(result)

    ArubaBleakClient.__name__ = f"ArubaBleakClient_{source.replace(':', '')}"
    return ArubaBleakClient


def build_service_collection(
    characteristics: list[ArubaCharacteristic],
    *,
    advertisement_service_uuids: set[str] | None = None,
):
    from bleak.backends.characteristic import BleakGATTCharacteristic
    from bleak.backends.service import BleakGATTService, BleakGATTServiceCollection

    services = BleakGATTServiceCollection()
    service_handles: dict[str, int] = {}
    known_characteristic_uuids: set[str] = set()
    next_handle = 1

    for characteristic in characteristics:
        if not characteristic.service_uuid or not characteristic.characteristic_uuid:
            continue
        service_uuid = _normalize_uuid(characteristic.service_uuid)
        characteristic_uuid = _normalize_uuid(characteristic.characteristic_uuid)

        service_handle = service_handles.get(service_uuid)
        if service_handle is None:
            service_handle = next_handle
            next_handle += 1
            service_handles[service_uuid] = service_handle
            services.add_service(
                BleakGATTService(
                    obj={"source": "aruba_ble_proxy"},
                    handle=service_handle,
                    uuid=service_uuid,
                )
            )

        service = services.get_service(service_uuid)
        if service is None:
            continue
        characteristic_handle = next_handle
        next_handle += 1
        services.add_characteristic(
            BleakGATTCharacteristic(
                obj={"source": "aruba_ble_proxy"},
                handle=characteristic_handle,
                uuid=characteristic_uuid,
                properties=aruba_properties_to_bleak(characteristic.properties),
                max_write_without_response_size=lambda: 20,
                service=service,
            )
        )
        known_characteristic_uuids.add(characteristic_uuid)

    if _should_add_switchbot_fallback(
        advertisement_service_uuids or set(),
        known_characteristic_uuids,
    ):
        next_handle = _add_switchbot_command_service(
            services,
            service_handles,
            next_handle,
        )

    return services


def aruba_properties_to_bleak(properties: tuple[str | int, ...]) -> list[str]:
    result: list[str] = []
    for prop in properties:
        value = ARUBA_TO_BLEAK_PROPERTIES.get(prop, prop) if isinstance(prop, str) else prop
        if isinstance(value, str) and value not in result:
            result.append(value)
    return result


def _service_collection_has_characteristics(services: Any) -> bool:
    characteristics = getattr(services, "characteristics", None)
    if isinstance(characteristics, (dict, list, tuple, set)):
        return bool(characteristics)

    service_map = getattr(services, "services", None)
    if isinstance(service_map, dict):
        return any(
            bool(getattr(service, "characteristics", None))
            for service in service_map.values()
        )

    return False


def _is_resolved_characteristic(characteristic: Any) -> bool:
    return bool(
        getattr(characteristic, "uuid", None)
        and getattr(characteristic, "service_uuid", None)
    )


def _is_local_fallback_characteristic(characteristic: Any) -> bool:
    obj = getattr(characteristic, "obj", None)
    return isinstance(obj, dict) and obj.get("source") == "aruba_ble_proxy"


def _should_add_switchbot_fallback(
    advertisement_service_uuids: set[str],
    known_characteristic_uuids: set[str],
) -> bool:
    return (
        SWITCHBOT_ADV_SERVICE_UUID
        in {_normalize_uuid(service_uuid) for service_uuid in advertisement_service_uuids}
        and (
            SWITCHBOT_READ_CHAR_UUID not in known_characteristic_uuids
            or SWITCHBOT_WRITE_CHAR_UUID not in known_characteristic_uuids
        )
    )


def _add_switchbot_command_service(
    services: Any,
    service_handles: dict[str, int],
    next_handle: int,
) -> int:
    from bleak.backends.characteristic import BleakGATTCharacteristic
    from bleak.backends.service import BleakGATTService

    service_handle = service_handles.get(SWITCHBOT_COMMAND_SERVICE_UUID)
    if service_handle is None:
        service_handle = next_handle
        next_handle += 1
        service_handles[SWITCHBOT_COMMAND_SERVICE_UUID] = service_handle
        services.add_service(
            BleakGATTService(
                obj={"source": "aruba_ble_proxy", "fallback": "switchbot"},
                handle=service_handle,
                uuid=SWITCHBOT_COMMAND_SERVICE_UUID,
            )
        )

    service = services.get_service(SWITCHBOT_COMMAND_SERVICE_UUID)
    if service is None:
        return next_handle

    for characteristic_uuid, properties in (
        (SWITCHBOT_WRITE_CHAR_UUID, ["write-without-response"]),
        (SWITCHBOT_READ_CHAR_UUID, ["notify", "read"]),
    ):
        if services.get_characteristic(characteristic_uuid) is not None:
            continue
        characteristic_handle = next_handle
        next_handle += 1
        services.add_characteristic(
            BleakGATTCharacteristic(
                obj={"source": "aruba_ble_proxy", "fallback": "switchbot"},
                handle=characteristic_handle,
                uuid=characteristic_uuid,
                properties=properties,
                max_write_without_response_size=lambda: 20,
                service=service,
            )
        )
    return next_handle


def _ble_device_address(value: Any) -> str | None:
    if isinstance(value, str):
        return _normalize_mac(value)
    address = getattr(value, "address", None)
    if isinstance(address, str):
        return _normalize_mac(address)
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


def _log_notify_callback_task_result(task: asyncio.Task) -> None:
    try:
        task.result()
    except asyncio.CancelledError:
        pass
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "Aruba BLE async notification callback failed"
        )


def _call_compatible_callback(callback: Any, arg_options: tuple[tuple[Any, ...], ...]):
    try:
        signature = inspect.signature(callback)
    except (TypeError, ValueError):
        last_error: TypeError | None = None
        for args in arg_options:
            try:
                return callback(*args)
            except TypeError as err:
                last_error = err
        if last_error is not None:
            raise last_error
        return callback()

    for args in arg_options:
        try:
            signature.bind(*args)
        except TypeError:
            continue
        return callback(*args)

    return callback(*arg_options[0])


def _make_notify_dispatcher(callback: Any):
    """Return a fast dispatcher that invokes ``callback`` with the right arity.

    The bleak callback contract accepts either ``callback(characteristic, value)``
    (modern) or ``callback(value)`` (legacy). We resolve the signature once at
    ``start_notify`` time so the per-notification hot path avoids repeated
    ``inspect.signature`` calls.
    """
    try:
        signature = inspect.signature(callback)
    except (TypeError, ValueError):
        def dispatch_uninspectable(char, value):
            try:
                return callback(char, value)
            except TypeError:
                return callback(value)

        return dispatch_uninspectable

    try:
        signature.bind(None, None)
    except TypeError:
        pass
    else:
        def dispatch_two(char, value):
            return callback(char, value)

        return dispatch_two

    try:
        signature.bind(None)
    except TypeError:
        pass
    else:
        def dispatch_one(char, value):
            return callback(value)

        return dispatch_one

    def dispatch_default(char, value):
        return callback(char, value)

    return dispatch_default


async def _call_wait_for_device_characteristics(
    runtime: Any,
    address: str,
    *,
    source: str,
):
    waiter = runtime.async_wait_for_device_characteristics
    try:
        signature = inspect.signature(waiter)
    except (TypeError, ValueError):
        return await waiter(address, source=source)
    if "source" in signature.parameters:
        return await waiter(address, source=source)
    return await waiter(address)


def _write_with_response_from_characteristic(characteristic: Any) -> bool:
    properties = set(getattr(characteristic, "properties", []) or [])
    if "write" in properties:
        return True
    if "write-without-response" in properties:
        return False
    return True


def _raise_for_failed_action(
    response: dict[str, Any],
    error_cls,
    *,
    allow_statuses: set[str] | None = None,
) -> None:
    result = response.get("result")
    if result is None:
        status = response.get("status")
        if status is None or status in LOCAL_SUCCESS_STATUSES or status in (allow_statuses or set()):
            return
        raise error_cls(
            "Aruba BLE local action failed: "
            + _status_detail(status, response.get("status_string"))
        )
    if result.get("received") is False:
        status = result.get("status", "missing_action_result")
        raise error_cls(
            "Aruba BLE action failed: "
            + _status_detail(status, result.get("status_string"))
        )
    status = result.get("status")
    if status == "success" or status in (allow_statuses or set()):
        return
    raise error_cls(
        "Aruba BLE action failed: "
        + _status_detail(status, result.get("status_string"))
    )


def _response_status(response: dict[str, Any]) -> str | None:
    result = response.get("result")
    if isinstance(result, dict):
        status = result.get("status")
        return str(status) if status is not None else None
    status = response.get("status")
    return str(status) if status is not None else None


def _status_detail(status: Any, status_string: Any = None) -> str:
    status_text = str(status) if status is not None else "unknown"
    if status_string:
        return f"{status_text} ({status_string})"
    return status_text
