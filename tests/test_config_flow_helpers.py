import importlib
import sys
import types


def _install_config_flow_stubs():
    voluptuous = types.ModuleType("voluptuous")
    voluptuous.Schema = lambda value: value
    voluptuous.Required = lambda key, default=None: key
    voluptuous.Optional = lambda key, default=None: key

    class ConfigFlow:
        def __init_subclass__(cls, **kwargs):
            super().__init_subclass__()

    class OptionsFlow:
        pass

    config_entries = types.ModuleType("homeassistant.config_entries")
    config_entries.ConfigFlow = ConfigFlow
    config_entries.OptionsFlow = OptionsFlow

    core = types.ModuleType("homeassistant.core")
    core.callback = lambda func: func

    homeassistant = types.ModuleType("homeassistant")
    homeassistant.config_entries = config_entries
    homeassistant.core = core

    sys.modules.setdefault("voluptuous", voluptuous)
    sys.modules.setdefault("homeassistant", homeassistant)
    sys.modules.setdefault("homeassistant.config_entries", config_entries)
    sys.modules.setdefault("homeassistant.core", core)


_install_config_flow_stubs()
config_flow = importlib.import_module("custom_components.aruba_ble_proxy.config_flow")

from custom_components.aruba_ble_proxy.const import (  # noqa: E402
    CONF_ACCESS_TOKEN,
    CONF_ENABLE_ACTIVE_BLE,
    CONF_ENDPOINT_PATH,
    CONF_LISTEN_PORT,
    CONF_PUBLIC_HOST,
    CONF_PUBLIC_SCHEME,
)


def test_data_defaults_enable_active_ble_for_current_experimental_build():
    data = config_flow._data_with_defaults({})

    assert data[CONF_ENABLE_ACTIVE_BLE] is True


def test_data_defaults_preserve_disabled_active_ble():
    data = config_flow._data_with_defaults({CONF_ENABLE_ACTIVE_BLE: False})

    assert data[CONF_ENABLE_ACTIVE_BLE] is False


def test_data_defaults_clean_endpoint_path():
    data = config_flow._data_with_defaults({CONF_ENDPOINT_PATH: "aruba"})

    assert data[CONF_ENDPOINT_PATH] == "/aruba"


def test_endpoint_url_forces_websocket_scheme_and_port():
    data = config_flow._data_with_defaults(
        {
            CONF_PUBLIC_HOST: "https://ha.example.local",
            CONF_LISTEN_PORT: 7443,
            CONF_ENDPOINT_PATH: "aruba-ble-proxy",
        }
    )

    assert (
        config_flow._endpoint_url(data)
        == "ws://ha.example.local:7443/aruba-ble-proxy"
    )


def test_endpoint_url_keeps_explicit_port():
    data = config_flow._data_with_defaults(
        {
            CONF_PUBLIC_HOST: "ws://ha.example.local:8123",
            CONF_LISTEN_PORT: 7443,
            CONF_ENDPOINT_PATH: "/aruba-ble-proxy",
        }
    )

    assert (
        config_flow._endpoint_url(data)
        == "ws://ha.example.local:8123/aruba-ble-proxy"
    )


def test_data_defaults_preserve_existing_token():
    data = config_flow._data_with_defaults({CONF_ACCESS_TOKEN: "secret"})

    assert data[CONF_ACCESS_TOKEN] == "secret"
    assert data[CONF_PUBLIC_SCHEME] == "ws"
