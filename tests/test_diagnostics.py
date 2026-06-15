from custom_components.aruba_ble_proxy.const import (
    CONF_ACCESS_TOKEN,
    CONF_ENTRY_TYPE,
    CONF_LISTEN_HOST,
    CONF_LISTEN_PORT,
    CONF_PUBLIC_HOST,
    CONF_PUBLIC_SCHEME,
    CONF_TRANSPORT_PREFIX,
    ENTRY_TYPE_LISTENER,
)
from custom_components.aruba_ble_proxy.diagnostics import async_get_config_entry_diagnostics
import asyncio


class _FakeRuntime:
    def diagnostic_attributes(self):
        return {
            "receiver_connected_sources": ["aa:bb:cc:dd:ee:ff"],
            "receiver_crashed": False,
        }


class _FakeEntry:
    data = {
        CONF_ENTRY_TYPE: ENTRY_TYPE_LISTENER,
        CONF_LISTEN_HOST: "0.0.0.0",
        CONF_LISTEN_PORT: 7443,
        CONF_PUBLIC_HOST: "ha.example.local",
        CONF_PUBLIC_SCHEME: "ws",
        CONF_TRANSPORT_PREFIX: "ha-ble",
        CONF_ACCESS_TOKEN: "secret",
    }
    options = {}
    runtime_data = _FakeRuntime()


def test_diagnostics_redacts_access_token():
    async def run_test():
        result = await async_get_config_entry_diagnostics(None, _FakeEntry())

        assert result["entry"][CONF_ACCESS_TOKEN] == "***redacted***"
        assert result["runtime"]["receiver_connected_sources"] == ["aa:bb:cc:dd:ee:ff"]

    asyncio.run(run_test())
