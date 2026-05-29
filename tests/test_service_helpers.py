from pathlib import Path

from custom_components.aruba_ble_proxy import (
    _endpoint_url,
    _parse_hex_value,
    _runtime_for_ap,
    _service_data_to_config,
)
from custom_components.aruba_ble_proxy.const import (
    CONF_ACCESS_TOKEN,
    CONF_ENABLE_RADIO_PROFILE,
    CONF_ENDPOINT_PATH,
    CONF_LISTEN_PORT,
    CONF_PUBLIC_HOST,
    CONF_PUBLIC_SCHEME,
    CONF_RADIO_PROFILE,
    CONF_TRANSPORT_PREFIX,
)


def test_service_cli_config_forces_ws_scheme_without_public_scheme_field():
    data = _service_data_to_config(
        {
            CONF_PUBLIC_HOST: "wss://ha.example.local",
            CONF_LISTEN_PORT: 7443,
            CONF_ENDPOINT_PATH: "aruba-ble-proxy",
            CONF_ACCESS_TOKEN: "token",
            CONF_TRANSPORT_PREFIX: "ha-ble",
            CONF_ENABLE_RADIO_PROFILE: True,
            CONF_RADIO_PROFILE: "ha-ble-radio",
        }
    )

    assert data[CONF_PUBLIC_SCHEME] == "ws"
    assert _endpoint_url(data) == "ws://ha.example.local:7443/aruba-ble-proxy"


def test_service_yaml_does_not_offer_unsupported_wss_option():
    services_yaml = Path("custom_components/aruba_ble_proxy/services.yaml").read_text(
        encoding="utf-8"
    )

    assert "public_scheme:" not in services_yaml
    assert "wss" not in services_yaml


def test_runtime_for_ap_normalizes_cli_service_source_mac():
    class Runtime:
        def __init__(self, sources):
            self.sources = sources

        def diagnostic_attributes(self):
            return {"receiver_connected_sources": self.sources}

    class Hass:
        data = {
            "aruba_ble_proxy": {
                "first": Runtime(["AA:BB:CC:DD:EE:FF"]),
                "second": Runtime(["02:00:00:00:00:01"]),
            }
        }

    runtime = _runtime_for_ap(Hass(), "020000000001")

    assert runtime.sources == ["02:00:00:00:00:01"]


def test_parse_hex_value_accepts_common_byte_separators():
    assert _parse_hex_value("57 0f:4e-01") == bytes.fromhex("570f4e01")
    assert _parse_hex_value("0x570f") == bytes.fromhex("570f")
    assert _parse_hex_value("") == b""


def test_parse_hex_value_rejects_odd_or_non_hex_input():
    try:
        _parse_hex_value("abc")
    except ValueError as err:
        assert "even number" in str(err)
    else:
        raise AssertionError("odd hex input should fail")

    try:
        _parse_hex_value("57 zz")
    except ValueError as err:
        assert "hexadecimal bytes" in str(err)
    else:
        raise AssertionError("non-hex input should fail")
