import logging

from .active import (
    ACTION_BLE_CONNECT,
    ACTION_BLE_DISCONNECT,
    ArubaBleActionRequest,
)
from .aruba_cli import (
    chunked,
    default_uuid_seed_path,
    parse_uuid_file,
    render_aruba_cleanup_config,
    render_aruba_config,
)

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ACTIVE_CONNECTION_SLOTS,
    CONF_ENTRY_TYPE,
    CONF_ENABLE_ACTIVE_BLE,
    CONF_ENABLE_RADIO_PROFILE,
    CONF_ENDPOINT_PATH,
    CONF_LISTEN_HOST,
    CONF_LISTEN_PORT,
    CONF_PUBLIC_HOST,
    CONF_PUBLIC_SCHEME,
    CONF_RADIO_PROFILE,
    CONF_TRANSPORT_PREFIX,
    DEFAULT_ACTIVE_CONNECTION_SLOTS,
    DOMAIN,
    ENTRY_TYPE_AP_SOURCE,
    SERVICE_BLE_CONNECT,
    SERVICE_BLE_DISCONNECT,
    SERVICE_GENERATE_CLI,
    SERVICE_GENERATE_CLEANUP_CLI,
    SERVICE_GATT_READ,
    SERVICE_GATT_NOTIFY,
    SERVICE_GATT_WRITE,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[str] = []


async def async_setup_entry(hass, entry) -> bool:
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_AP_SOURCE:
        return True

    from .runtime import ArubaBleProxyRuntime

    runtime = ArubaBleProxyRuntime(
        hass=hass,
        host=entry.data[CONF_LISTEN_HOST],
        port=entry.data[CONF_LISTEN_PORT],
        access_token=entry.data[CONF_ACCESS_TOKEN],
        enable_active_ble=entry.data.get(CONF_ENABLE_ACTIVE_BLE, True),
        active_connection_slots=entry.data.get(
            CONF_ACTIVE_CONNECTION_SLOTS,
            DEFAULT_ACTIVE_CONNECTION_SLOTS,
        ),
    )
    await runtime.async_start(entry)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = runtime
    if PLATFORMS:
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    return True


async def async_unload_entry(hass, entry) -> bool:
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_AP_SOURCE:
        return True

    unload_ok = True
    if PLATFORMS:
        unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    runtime: ArubaBleProxyRuntime | None = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if runtime is not None:
        await runtime.async_stop()
    return unload_ok


async def _async_update_listener(hass, entry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_setup(hass, config: dict) -> bool:
    from homeassistant.core import SupportsResponse

    async def _async_generate_cli(call) -> dict[str, str]:
        data = _service_data_to_config(call.data)
        return await hass.async_add_executor_job(_generate_cli_response, data)

    async def _async_generate_cleanup_cli(call) -> dict[str, str]:
        data = _service_data_to_config(call.data)
        return await hass.async_add_executor_job(_generate_cleanup_cli_response, data)

    async def _async_ble_connect(call) -> dict:
        runtime = _runtime_for_ap(hass, call.data["ap_mac"])
        return await runtime.async_send_aruba_action(
            ap_mac=call.data["ap_mac"],
            request=ArubaBleActionRequest(
                action_type=ACTION_BLE_CONNECT,
                device_mac=call.data["device_mac"],
                timeout=call.data["timeout"],
            ),
            wait_result=call.data["wait_result"],
        )

    async def _async_ble_disconnect(call) -> dict:
        runtime = _runtime_for_ap(hass, call.data["ap_mac"])
        return await runtime.async_send_aruba_action(
            ap_mac=call.data["ap_mac"],
            request=ArubaBleActionRequest(
                action_type=ACTION_BLE_DISCONNECT,
                device_mac=call.data["device_mac"],
                timeout=call.data["timeout"],
            ),
            wait_result=call.data["wait_result"],
        )

    async def _async_gatt_read(call) -> dict:
        runtime = _runtime_for_ap(hass, call.data["ap_mac"])
        return await runtime.async_gatt_read(
            ap_mac=call.data["ap_mac"],
            device_mac=call.data["device_mac"],
            service_uuid=call.data["service_uuid"],
            characteristic_uuid=call.data["characteristic_uuid"],
            timeout=call.data["timeout"],
            wait_result=call.data["wait_result"],
        )

    async def _async_gatt_write(call) -> dict:
        runtime = _runtime_for_ap(hass, call.data["ap_mac"])
        return await runtime.async_gatt_write(
            ap_mac=call.data["ap_mac"],
            device_mac=call.data["device_mac"],
            service_uuid=call.data["service_uuid"],
            characteristic_uuid=call.data["characteristic_uuid"],
            value=_parse_hex_value(call.data["value"]),
            with_response=call.data["with_response"],
            timeout=call.data["timeout"],
            wait_result=call.data["wait_result"],
        )

    async def _async_gatt_notify(call) -> dict:
        runtime = _runtime_for_ap(hass, call.data["ap_mac"])
        return await runtime.async_gatt_notification(
            ap_mac=call.data["ap_mac"],
            device_mac=call.data["device_mac"],
            service_uuid=call.data["service_uuid"],
            characteristic_uuid=call.data["characteristic_uuid"],
            enable=call.data["enable"],
            indicate=call.data["indicate"],
            timeout=call.data["timeout"],
            wait_result=call.data["wait_result"],
        )

    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_CLI,
        _async_generate_cli,
        schema=_cli_service_schema(),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GENERATE_CLEANUP_CLI,
        _async_generate_cleanup_cli,
        schema=_cli_service_schema(),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_BLE_CONNECT,
        _async_ble_connect,
        schema=_ble_action_service_schema(),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_BLE_DISCONNECT,
        _async_ble_disconnect,
        schema=_ble_action_service_schema(),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GATT_READ,
        _async_gatt_read,
        schema=_gatt_action_service_schema(include_value=False),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GATT_WRITE,
        _async_gatt_write,
        schema=_gatt_action_service_schema(include_value=True),
        supports_response=SupportsResponse.ONLY,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_GATT_NOTIFY,
        _async_gatt_notify,
        schema=_gatt_notify_service_schema(),
        supports_response=SupportsResponse.ONLY,
    )
    return True


def _generate_cli_response(data: dict) -> dict[str, str]:
    return {"cli": _generate_cli(data), "endpoint_url": _endpoint_url(data)}


def _generate_cleanup_cli_response(data: dict) -> dict[str, str]:
    return {"cli": _generate_cleanup_cli(data)}


def _cli_service_schema():
    import voluptuous as vol
    from homeassistant.helpers import config_validation as cv

    return vol.Schema(
        {
            vol.Required(CONF_PUBLIC_HOST): cv.string,
            vol.Required(CONF_LISTEN_PORT, default=7443): cv.port,
            vol.Required(CONF_ENDPOINT_PATH, default="/aruba-ble-proxy"): cv.string,
            vol.Required(CONF_ACCESS_TOKEN): cv.string,
            vol.Required(CONF_TRANSPORT_PREFIX, default="ha-ble"): cv.string,
            vol.Required(CONF_ENABLE_RADIO_PROFILE, default=True): cv.boolean,
            vol.Required(CONF_RADIO_PROFILE, default="ha-ble-radio"): cv.string,
        }
    )


def _ble_action_service_schema():
    import voluptuous as vol
    from homeassistant.helpers import config_validation as cv

    return vol.Schema(
        {
            vol.Required("ap_mac"): cv.string,
            vol.Required("device_mac"): cv.string,
            vol.Optional("timeout", default=20): cv.positive_int,
            vol.Optional("wait_result", default=True): cv.boolean,
        }
    )


def _gatt_action_service_schema(*, include_value: bool):
    import voluptuous as vol
    from homeassistant.helpers import config_validation as cv

    schema = {
        vol.Required("ap_mac"): cv.string,
        vol.Required("device_mac"): cv.string,
        vol.Required("service_uuid"): cv.string,
        vol.Required("characteristic_uuid"): cv.string,
        vol.Optional("timeout", default=20): cv.positive_int,
        vol.Optional("wait_result", default=True): cv.boolean,
    }
    if include_value:
        schema[vol.Required("value")] = cv.string
        schema[vol.Optional("with_response", default=True)] = cv.boolean
    return vol.Schema(schema)


def _gatt_notify_service_schema():
    import voluptuous as vol
    from homeassistant.helpers import config_validation as cv

    return vol.Schema(
        {
            vol.Required("ap_mac"): cv.string,
            vol.Required("device_mac"): cv.string,
            vol.Required("service_uuid"): cv.string,
            vol.Required("characteristic_uuid"): cv.string,
            vol.Optional("enable", default=True): cv.boolean,
            vol.Optional("indicate", default=False): cv.boolean,
            vol.Optional("timeout", default=20): cv.positive_int,
            vol.Optional("wait_result", default=True): cv.boolean,
        }
    )


def _runtime_for_ap(hass, ap_mac: str):
    normalized_ap = _normalize_mac(ap_mac) or ap_mac.upper()
    for runtime in hass.data.get(DOMAIN, {}).values():
        connected_sources = runtime.diagnostic_attributes().get("receiver_connected_sources", [])
        normalized_sources = {
            _normalize_mac(source) or str(source).upper()
            for source in connected_sources
        }
        if normalized_ap in normalized_sources:
            return runtime
    runtimes = list(hass.data.get(DOMAIN, {}).values())
    if len(runtimes) == 1:
        return runtimes[0]
    raise ValueError(f"No Aruba BLE Proxy runtime is connected to AP {ap_mac}")


def _service_data_to_config(data) -> dict:
    return {
        CONF_PUBLIC_HOST: data[CONF_PUBLIC_HOST],
        CONF_PUBLIC_SCHEME: "ws",
        CONF_LISTEN_PORT: data[CONF_LISTEN_PORT],
        CONF_ENDPOINT_PATH: data[CONF_ENDPOINT_PATH],
        CONF_ACCESS_TOKEN: data[CONF_ACCESS_TOKEN],
        CONF_TRANSPORT_PREFIX: data[CONF_TRANSPORT_PREFIX],
        CONF_ENABLE_RADIO_PROFILE: data[CONF_ENABLE_RADIO_PROFILE],
        CONF_RADIO_PROFILE: data[CONF_RADIO_PROFILE],
    }


def _parse_hex_value(value: str) -> bytes:
    compact = (
        str(value)
        .strip()
        .replace(" ", "")
        .replace("\n", "")
        .replace("\t", "")
        .replace(":", "")
        .replace("-", "")
    )
    if not compact:
        return b""
    if compact.startswith(("0x", "0X")):
        compact = compact[2:]
    if len(compact) % 2:
        raise ValueError("GATT write value must contain an even number of hex digits")
    try:
        return bytes.fromhex(compact)
    except ValueError as err:
        raise ValueError(
            "GATT write value must be hexadecimal bytes, for example '57 0f 4e'"
        ) from err


def _endpoint_url(data: dict) -> str:
    host = str(data[CONF_PUBLIC_HOST]).strip().rstrip("/")
    for prefix in ("http://", "https://", "ws://", "wss://"):
        if host.startswith(prefix):
            host = host.removeprefix(prefix)
    if ":" not in host.rsplit("/", 1)[0]:
        host = f"{host}:{data[CONF_LISTEN_PORT]}"
    path = str(data[CONF_ENDPOINT_PATH]).strip() or "/aruba-ble-proxy"
    if not path.startswith("/"):
        path = f"/{path}"
    return f"{data[CONF_PUBLIC_SCHEME]}://{host}{path}"


def _generate_cli(data: dict) -> str:
    uuids = parse_uuid_file(default_uuid_seed_path())
    return render_aruba_config(
        uuids=uuids,
        name_prefix=data[CONF_TRANSPORT_PREFIX],
        endpoint_url=_endpoint_url(data),
        token=data[CONF_ACCESS_TOKEN],
        radio_profile=data[CONF_RADIO_PROFILE] if data[CONF_ENABLE_RADIO_PROFILE] else None,
    )


def _generate_cleanup_cli(data: dict) -> str:
    uuids = parse_uuid_file(default_uuid_seed_path())
    return render_aruba_cleanup_config(
        name_prefix=data[CONF_TRANSPORT_PREFIX],
        profile_count=len(chunked(uuids, 10)),
        radio_profile=data[CONF_RADIO_PROFILE] if data[CONF_ENABLE_RADIO_PROFILE] else None,
    )


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
