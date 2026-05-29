from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import EntityCategory

from .const import DOMAIN


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    runtime = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        [
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="ble_advertisements",
                name="BLE advertisements",
                icon="mdi:bluetooth",
                value_fn=lambda runtime: runtime.stats.events,
                attrs=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="bluetooth_forwards",
                name="Bluetooth forwards",
                icon="mdi:bluetooth-transfer",
                value_fn=lambda runtime: runtime.stats.bluetooth_forwards,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="bluetooth_forward_errors",
                name="Bluetooth forward errors",
                icon="mdi:bluetooth-off",
                value_fn=lambda runtime: runtime.stats.bluetooth_forward_errors,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="registered_scanners",
                name="Registered scanners",
                icon="mdi:access-point-network",
                value_fn=lambda runtime: runtime.diagnostic_attributes()["registered_scanners"],
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="last_advertisement",
                name="Last advertisement",
                icon="mdi:bluetooth-connect",
                value_fn=lambda runtime: runtime.diagnostic_attributes()["last_address"] or "unknown",
                diagnostic=True,
                attrs=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="last_bluetooth_error",
                name="Last Bluetooth error",
                icon="mdi:bluetooth-off",
                value_fn=lambda runtime: runtime.diagnostic_attributes()["last_bluetooth_error"]
                or "none",
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_actions_sent",
                name="Active BLE actions sent",
                icon="mdi:bluetooth-transfer",
                value_fn=lambda runtime: runtime.stats.active_actions_sent,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_action_failures",
                name="Active BLE action failures",
                icon="mdi:bluetooth-off",
                value_fn=lambda runtime: runtime.stats.active_action_failures,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_action_results",
                name="Active BLE action results",
                icon="mdi:message-processing-outline",
                value_fn=lambda runtime: runtime.stats.active_action_results,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_action_send_errors",
                name="Active BLE action send errors",
                icon="mdi:send-alert-outline",
                value_fn=lambda runtime: runtime.stats.active_action_send_errors,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_action_timeouts",
                name="Active BLE action timeouts",
                icon="mdi:timer-alert-outline",
                value_fn=lambda runtime: runtime.stats.active_action_timeouts,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_action_orphan_results",
                name="Active BLE orphan action results",
                icon="mdi:message-alert-outline",
                value_fn=lambda runtime: runtime.stats.active_action_orphan_results,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_status_updates",
                name="Active BLE status updates",
                icon="mdi:bluetooth-settings",
                value_fn=lambda runtime: runtime.stats.active_status_updates,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_disconnect_statuses",
                name="Active BLE disconnect statuses",
                icon="mdi:bluetooth-off",
                value_fn=lambda runtime: runtime.stats.active_disconnect_statuses,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_source_disconnects",
                name="Active BLE source disconnects",
                icon="mdi:access-point-network-off",
                value_fn=lambda runtime: runtime.stats.active_source_disconnects,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_connectable_scanners",
                name="Active BLE connectable scanners",
                icon="mdi:access-point-network",
                value_fn=lambda runtime: runtime.stats.active_connectable_scanners,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_operations_in_flight",
                name="Active BLE operations in flight",
                icon="mdi:progress-clock",
                value_fn=lambda runtime: runtime.diagnostic_attributes()[
                    "active_operations_in_flight"
                ],
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_operations_waiting",
                name="Active BLE operations waiting",
                icon="mdi:timer-sand",
                value_fn=lambda runtime: runtime.diagnostic_attributes()[
                    "active_operations_waiting"
                ],
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_characteristics",
                name="Active BLE characteristics",
                icon="mdi:format-list-bulleted",
                value_fn=lambda runtime: runtime.stats.active_characteristics,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_characteristic_waits",
                name="Active BLE characteristic waits",
                icon="mdi:format-list-checks",
                value_fn=lambda runtime: runtime.stats.active_characteristic_waits,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_characteristic_wait_timeouts",
                name="Active BLE characteristic wait timeouts",
                icon="mdi:timer-alert-outline",
                value_fn=lambda runtime: runtime.stats.active_characteristic_wait_timeouts,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_notifications_enabled",
                name="Active BLE notifications enabled",
                icon="mdi:bell-ring-outline",
                value_fn=lambda runtime: runtime.stats.active_notifications_enabled,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_notification_updates",
                name="Active BLE notification updates",
                icon="mdi:bell-check-outline",
                value_fn=lambda runtime: runtime.stats.active_notification_updates,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_notification_callback_errors",
                name="Active BLE notification callback errors",
                icon="mdi:bell-alert-outline",
                value_fn=lambda runtime: runtime.stats.active_notification_callback_errors,
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_last_action",
                name="Active BLE last action",
                icon="mdi:bluetooth-connect",
                value_fn=lambda runtime: runtime.diagnostic_attributes()[
                    "last_active_action_status"
                ]
                or "none",
                diagnostic=True,
                attrs=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_last_action_duration",
                name="Active BLE last action duration",
                icon="mdi:timer-outline",
                value_fn=lambda runtime: runtime.diagnostic_attributes()[
                    "last_active_action_duration_ms"
                ]
                or 0,
                diagnostic=True,
                attrs=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_slowest_action_duration",
                name="Active BLE slowest action duration",
                icon="mdi:timer-alert-outline",
                value_fn=lambda runtime: runtime.diagnostic_attributes()[
                    "slowest_active_action_duration_ms"
                ]
                or 0,
                diagnostic=True,
                attrs=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_last_characteristic_wait_duration",
                name="Active BLE last characteristic wait duration",
                icon="mdi:timer-outline",
                value_fn=lambda runtime: runtime.diagnostic_attributes()[
                    "last_active_characteristic_wait_duration_ms"
                ]
                or 0,
                diagnostic=True,
                attrs=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_slowest_characteristic_wait_duration",
                name="Active BLE slowest characteristic wait duration",
                icon="mdi:timer-alert-outline",
                value_fn=lambda runtime: runtime.diagnostic_attributes()[
                    "slowest_active_characteristic_wait_duration_ms"
                ]
                or 0,
                diagnostic=True,
                attrs=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_last_action_error",
                name="Active BLE last action error",
                icon="mdi:alert-circle-outline",
                value_fn=lambda runtime: runtime.diagnostic_attributes()[
                    "last_active_action_error"
                ]
                or "none",
                diagnostic=True,
                attrs=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_debug_summary",
                name="Active BLE debug summary",
                icon="mdi:bug-outline",
                value_fn=_active_debug_summary,
                diagnostic=True,
                attrs=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="active_last_status",
                name="Active BLE last status",
                icon="mdi:bluetooth-settings",
                value_fn=lambda runtime: runtime.diagnostic_attributes()[
                    "last_active_status"
                ]
                or "none",
                diagnostic=True,
                attrs=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="receiver_running",
                name="Receiver running",
                icon="mdi:server-network",
                value_fn=lambda runtime: runtime.diagnostic_attributes()["receiver_running"],
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="websocket_connections",
                name="WebSocket connections",
                icon="mdi:web",
                value_fn=lambda runtime: runtime.diagnostic_attributes()["receiver_connections_opened"],
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="websocket_messages",
                name="WebSocket messages",
                icon="mdi:message-arrow-right-outline",
                value_fn=lambda runtime: runtime.diagnostic_attributes()["receiver_binary_messages"],
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="invalid_tokens",
                name="Invalid tokens",
                icon="mdi:lock-alert",
                value_fn=lambda runtime: runtime.diagnostic_attributes()["receiver_invalid_tokens"],
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="decode_errors",
                name="Decode errors",
                icon="mdi:alert-circle-outline",
                value_fn=lambda runtime: runtime.diagnostic_attributes()["receiver_decode_errors"],
                diagnostic=True,
            ),
            ArubaBleProxyDiagnosticSensor(
                entry,
                runtime,
                key="last_peer",
                name="Last peer",
                icon="mdi:access-point-network",
                value_fn=lambda runtime: runtime.diagnostic_attributes()["receiver_last_peer"] or "unknown",
                diagnostic=True,
            ),
        ]
    )


def _active_debug_summary(runtime) -> str:
    attrs = runtime.diagnostic_attributes()
    in_flight = attrs["active_operations_in_flight"]
    waiting = attrs["active_operations_waiting"]
    last_action = attrs["last_active_action_type"] or "none"
    last_status = attrs["last_active_action_status"] or "none"
    last_ms = attrs["last_active_action_duration_ms"]
    slow_action = attrs["slowest_active_action_type"] or "none"
    slow_status = attrs["slowest_active_action_status"] or "none"
    slow_ms = attrs["slowest_active_action_duration_ms"]
    wait_status = attrs["last_active_characteristic_wait_status"] or "none"
    wait_ms = attrs["last_active_characteristic_wait_duration_ms"]
    slow_wait_status = attrs["slowest_active_characteristic_wait_status"] or "none"
    slow_wait_ms = attrs["slowest_active_characteristic_wait_duration_ms"]
    return (
        f"flight={in_flight} wait={waiting} "
        f"last={last_action}/{last_status}/{_format_ms(last_ms)} "
        f"slow={slow_action}/{slow_status}/{_format_ms(slow_ms)} "
        f"chars={wait_status}/{_format_ms(wait_ms)} "
        f"slowchars={slow_wait_status}/{_format_ms(slow_wait_ms)}"
    )


def _format_ms(value: int | None) -> str:
    if value is None:
        return "n/a"
    return f"{value}ms"


class ArubaBleProxyDiagnosticSensor(SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self,
        entry: ConfigEntry,
        runtime,
        *,
        key: str,
        name: str,
        icon: str,
        value_fn,
        attrs: bool = False,
        diagnostic: bool = False,
    ) -> None:
        self._entry = entry
        self._runtime = runtime
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_name = name
        self._attr_icon = icon
        self._value_fn = value_fn
        self._include_attrs = attrs
        if diagnostic:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC
            self._attr_entity_registry_enabled_default = False
        self._remove_listener = None

    @property
    def native_value(self):
        return self._value_fn(self._runtime)

    @property
    def extra_state_attributes(self):
        if not self._include_attrs:
            return None
        return self._runtime.diagnostic_attributes()

    async def async_added_to_hass(self) -> None:
        self._remove_listener = self._runtime.async_add_listener(self._async_stats_updated)

    async def async_will_remove_from_hass(self) -> None:
        if self._remove_listener is not None:
            self._remove_listener()
            self._remove_listener = None

    @callback
    def _async_stats_updated(self) -> None:
        self.async_write_ha_state()
