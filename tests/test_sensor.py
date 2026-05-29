import asyncio
import importlib
import sys
import types
from types import SimpleNamespace

from custom_components.aruba_ble_proxy.const import DOMAIN


def _install_fake_homeassistant(monkeypatch):
    class SensorEntity:
        def async_write_ha_state(self):
            return None

    class EntityCategory:
        DIAGNOSTIC = "diagnostic"

    def callback(func):
        return func

    modules = {
        "homeassistant": types.ModuleType("homeassistant"),
        "homeassistant.components": types.ModuleType("homeassistant.components"),
        "homeassistant.components.sensor": types.ModuleType(
            "homeassistant.components.sensor"
        ),
        "homeassistant.config_entries": types.ModuleType(
            "homeassistant.config_entries"
        ),
        "homeassistant.core": types.ModuleType("homeassistant.core"),
        "homeassistant.helpers": types.ModuleType("homeassistant.helpers"),
        "homeassistant.helpers.entity_platform": types.ModuleType(
            "homeassistant.helpers.entity_platform"
        ),
        "homeassistant.helpers.entity": types.ModuleType(
            "homeassistant.helpers.entity"
        ),
    }
    modules["homeassistant.components.sensor"].SensorEntity = SensorEntity
    modules["homeassistant.config_entries"].ConfigEntry = object
    modules["homeassistant.core"].HomeAssistant = object
    modules["homeassistant.core"].callback = callback
    modules["homeassistant.helpers.entity_platform"].AddEntitiesCallback = object
    modules["homeassistant.helpers.entity"].EntityCategory = EntityCategory

    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)


def test_sensor_setup_exposes_active_ble_diagnostics(monkeypatch):
    _install_fake_homeassistant(monkeypatch)
    sensor_module = importlib.import_module("custom_components.aruba_ble_proxy.sensor")

    class Runtime:
        def __init__(self):
            self.stats = SimpleNamespace(
                events=0,
                bluetooth_forwards=0,
                bluetooth_forward_errors=0,
                active_actions_sent=3,
                active_action_failures=1,
                active_action_results=18,
                active_action_send_errors=2,
                active_action_timeouts=4,
                active_action_orphan_results=5,
                active_status_updates=6,
                active_disconnect_statuses=7,
                active_source_disconnects=8,
                active_characteristics=9,
                active_characteristic_waits=10,
                active_characteristic_wait_timeouts=11,
                active_connectable_scanners=12,
                active_notifications_enabled=13,
                active_notification_updates=14,
                active_notification_callback_errors=15,
            )

        def async_add_listener(self, listener):
            return lambda: None

        def diagnostic_attributes(self):
            return {
                "registered_scanners": 0,
                "last_address": None,
                "last_bluetooth_error": None,
                "last_active_action_status": "gattError",
                "last_active_action_error": "gattError: failed",
                "last_active_action_type": "gattWrite",
                "last_active_action_duration_ms": 2100,
                "slowest_active_action_type": "bleConnect",
                "slowest_active_action_status": "success",
                "slowest_active_action_duration_ms": 5300,
                "last_active_characteristic_wait_status": "timeout",
                "last_active_characteristic_wait_duration_ms": 3000,
                "slowest_active_characteristic_wait_status": "timeout",
                "slowest_active_characteristic_wait_duration_ms": 3000,
                "last_active_status": "connectionUpdate",
                "active_operations_in_flight": 16,
                "active_operations_waiting": 17,
                "receiver_running": True,
                "receiver_connections_opened": 0,
                "receiver_binary_messages": 0,
                "receiver_invalid_tokens": 0,
                "receiver_decode_errors": 0,
                "receiver_last_peer": None,
            }

    entry = SimpleNamespace(entry_id="entry-1")
    hass = SimpleNamespace(data={DOMAIN: {entry.entry_id: Runtime()}})
    entities = []

    asyncio.run(sensor_module.async_setup_entry(hass, entry, entities.extend))

    entities_by_key = {
        entity._attr_unique_id.removeprefix("entry-1_"): entity
        for entity in entities
    }

    assert entities_by_key["active_actions_sent"].native_value == 3
    assert entities_by_key["active_action_failures"].native_value == 1
    assert entities_by_key["active_action_results"].native_value == 18
    assert entities_by_key["active_action_send_errors"].native_value == 2
    assert entities_by_key["active_action_timeouts"].native_value == 4
    assert entities_by_key["active_action_orphan_results"].native_value == 5
    assert entities_by_key["active_status_updates"].native_value == 6
    assert entities_by_key["active_disconnect_statuses"].native_value == 7
    assert entities_by_key["active_source_disconnects"].native_value == 8
    assert entities_by_key["active_characteristics"].native_value == 9
    assert entities_by_key["active_characteristic_waits"].native_value == 10
    assert entities_by_key["active_characteristic_wait_timeouts"].native_value == 11
    assert entities_by_key["active_connectable_scanners"].native_value == 12
    assert entities_by_key["active_notifications_enabled"].native_value == 13
    assert entities_by_key["active_notification_updates"].native_value == 14
    assert entities_by_key["active_notification_callback_errors"].native_value == 15
    assert entities_by_key["active_operations_in_flight"].native_value == 16
    assert entities_by_key["active_operations_waiting"].native_value == 17
    assert entities_by_key["active_last_action"].native_value == "gattError"
    assert entities_by_key["active_debug_summary"].native_value == (
        "flight=16 wait=17 last=gattWrite/gattError/2100ms "
        "slow=bleConnect/success/5300ms chars=timeout/3000ms "
        "slowchars=timeout/3000ms"
    )
    assert entities_by_key["active_last_action_duration"].native_value == 2100
    assert entities_by_key["active_slowest_action_duration"].native_value == 5300
    assert (
        entities_by_key["active_last_characteristic_wait_duration"].native_value
        == 3000
    )
    assert (
        entities_by_key["active_slowest_characteristic_wait_duration"].native_value
        == 3000
    )
    assert entities_by_key["active_last_action_error"].native_value == "gattError: failed"
    assert entities_by_key["active_last_status"].native_value == "connectionUpdate"
    assert entities_by_key["active_last_action"].extra_state_attributes[
        "last_active_action_status"
    ] == "gattError"

    for key in (
        "active_actions_sent",
        "active_action_failures",
        "active_action_results",
        "active_action_send_errors",
        "active_action_timeouts",
        "active_action_orphan_results",
        "active_status_updates",
        "active_disconnect_statuses",
        "active_source_disconnects",
        "active_connectable_scanners",
        "active_operations_in_flight",
        "active_operations_waiting",
        "active_characteristics",
        "active_characteristic_waits",
        "active_characteristic_wait_timeouts",
        "active_notifications_enabled",
        "active_notification_updates",
        "active_notification_callback_errors",
        "active_last_action",
        "active_last_action_duration",
        "active_slowest_action_duration",
        "active_last_characteristic_wait_duration",
        "active_slowest_characteristic_wait_duration",
        "active_last_action_error",
        "active_debug_summary",
        "active_last_status",
    ):
        assert entities_by_key[key]._attr_entity_category == "diagnostic"
        assert entities_by_key[key]._attr_entity_registry_enabled_default is False
