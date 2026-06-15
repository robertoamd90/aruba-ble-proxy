import sys
import types

from aruba_iot_ble.compatibility import (
    SWITCHBOT_READ_CHAR_UUID,
    SWITCHBOT_WRITE_CHAR_UUID,
    apply_gatt_overrides,
)


class _FakeService:
    def __init__(self, *, obj, handle, uuid):
        self.obj = obj
        self.handle = handle
        self.uuid = uuid
        self.characteristics = []


class _FakeCharacteristic:
    def __init__(
        self,
        *,
        obj,
        handle,
        uuid,
        properties,
        max_write_without_response_size,
        service,
    ):
        self.obj = obj
        self.handle = handle
        self.uuid = uuid
        self.properties = properties
        self.max_write_without_response_size = max_write_without_response_size
        self.service_uuid = service.uuid
        self.service_handle = service.handle


class _FakeServiceCollection:
    def __init__(self):
        self.services = {}
        self.characteristics = {}

    def add_service(self, service):
        self.services[service.uuid] = service

    def get_service(self, specifier):
        return self.services.get(specifier)

    def add_characteristic(self, characteristic):
        self.characteristics[characteristic.uuid] = characteristic
        self.services[characteristic.service_uuid].characteristics.append(characteristic)

    def get_characteristic(self, specifier):
        return self.characteristics.get(specifier)


def test_apply_gatt_overrides_adds_switchbot_command_service(monkeypatch):
    modules = {
        "bleak": types.ModuleType("bleak"),
        "bleak.backends": types.ModuleType("bleak.backends"),
        "bleak.backends.service": types.ModuleType("bleak.backends.service"),
        "bleak.backends.characteristic": types.ModuleType("bleak.backends.characteristic"),
    }
    modules["bleak.backends.service"].BleakGATTService = _FakeService
    modules["bleak.backends.service"].BleakGATTServiceCollection = _FakeServiceCollection
    modules["bleak.backends.characteristic"].BleakGATTCharacteristic = _FakeCharacteristic
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)

    services = _FakeServiceCollection()
    applied = apply_gatt_overrides(
        services,
        advertised_service_uuids={"fd3d"},
        known_characteristic_uuids=set(),
    )

    assert applied == ["switchbot_fd3d_command_service"]
    assert services.get_characteristic(SWITCHBOT_READ_CHAR_UUID) is not None
    assert services.get_characteristic(SWITCHBOT_WRITE_CHAR_UUID) is not None
