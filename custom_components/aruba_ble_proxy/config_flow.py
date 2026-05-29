from __future__ import annotations

import secrets
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from .aruba_cli import (
    chunked,
    default_uuid_seed_path,
    parse_uuid_file,
    render_aruba_cleanup_config,
    render_aruba_config,
)

from homeassistant import config_entries
from homeassistant.core import callback

from .const import (
    CONF_ACCESS_TOKEN,
    CONF_ENABLE_RADIO_PROFILE,
    CONF_ENABLE_ACTIVE_BLE,
    CONF_ENDPOINT_PATH,
    CONF_LISTEN_HOST,
    CONF_LISTEN_PORT,
    CONF_PUBLIC_HOST,
    CONF_PUBLIC_SCHEME,
    CONF_RADIO_PROFILE,
    CONF_SETUP_COMPLETE,
    CONF_TRANSPORT_PREFIX,
    DEFAULT_ENDPOINT_PATH,
    DEFAULT_ENABLE_ACTIVE_BLE,
    DEFAULT_LISTEN_HOST,
    DEFAULT_LISTEN_PORT,
    DEFAULT_PUBLIC_SCHEME,
    DEFAULT_RADIO_PROFILE,
    DEFAULT_TRANSPORT_PREFIX,
    DOMAIN,
)


def _default_public_host(hass) -> str:
    url = getattr(hass.config, "internal_url", None) or getattr(hass.config, "external_url", None) or ""
    if not url:
        return ""
    parsed = urlparse(url)
    return parsed.hostname or url


def _clean_path(path: str) -> str:
    path = path.strip() or DEFAULT_ENDPOINT_PATH
    return path if path.startswith("/") else f"/{path}"


def _endpoint_url(data: dict[str, Any]) -> str:
    host = data[CONF_PUBLIC_HOST].strip().rstrip("/")
    scheme = data[CONF_PUBLIC_SCHEME]
    path = _clean_path(data[CONF_ENDPOINT_PATH])
    if host.startswith("http://"):
        host = host.removeprefix("http://")
    if host.startswith("https://"):
        host = host.removeprefix("https://")
    if host.startswith("ws://"):
        host = host.removeprefix("ws://")
    if host.startswith("wss://"):
        host = host.removeprefix("wss://")
    if ":" not in host.rsplit("/", 1)[0]:
        host = f"{host}:{data[CONF_LISTEN_PORT]}"
    return f"{scheme}://{host}{path}"


def _generate_cli(data: dict[str, Any]) -> str:
    uuids = parse_uuid_file(default_uuid_seed_path())
    return render_aruba_config(
        uuids=uuids,
        name_prefix=data[CONF_TRANSPORT_PREFIX],
        endpoint_url=_endpoint_url(data),
        token=data[CONF_ACCESS_TOKEN],
        radio_profile=data[CONF_RADIO_PROFILE] if data[CONF_ENABLE_RADIO_PROFILE] else None,
    )


def _generate_cleanup_cli(data: dict[str, Any]) -> str:
    uuids = parse_uuid_file(default_uuid_seed_path())
    return render_aruba_cleanup_config(
        name_prefix=data[CONF_TRANSPORT_PREFIX],
        profile_count=len(chunked(uuids, 10)),
        radio_profile=data[CONF_RADIO_PROFILE] if data[CONF_ENABLE_RADIO_PROFILE] else None,
    )


def _cli_profile_count() -> int:
    uuids = parse_uuid_file(default_uuid_seed_path())
    return len(chunked(uuids, 10))


def _cli_filter_count() -> int:
    return len(parse_uuid_file(default_uuid_seed_path()))


def _data_with_defaults(data: dict[str, Any]) -> dict[str, Any]:
    merged = {
        CONF_LISTEN_HOST: DEFAULT_LISTEN_HOST,
        CONF_LISTEN_PORT: DEFAULT_LISTEN_PORT,
        CONF_PUBLIC_SCHEME: DEFAULT_PUBLIC_SCHEME,
        CONF_PUBLIC_HOST: "",
        CONF_ENDPOINT_PATH: DEFAULT_ENDPOINT_PATH,
        CONF_ACCESS_TOKEN: "",
        CONF_TRANSPORT_PREFIX: DEFAULT_TRANSPORT_PREFIX,
        CONF_ENABLE_RADIO_PROFILE: True,
        CONF_ENABLE_ACTIVE_BLE: DEFAULT_ENABLE_ACTIVE_BLE,
        CONF_RADIO_PROFILE: DEFAULT_RADIO_PROFILE,
        CONF_SETUP_COMPLETE: False,
    }
    merged.update(data)
    merged[CONF_ENDPOINT_PATH] = _clean_path(str(merged[CONF_ENDPOINT_PATH]))
    return merged


class ArubaBleProxyConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_user(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            data = _data_with_defaults(dict(user_input))
            data[CONF_LISTEN_HOST] = DEFAULT_LISTEN_HOST
            data[CONF_PUBLIC_SCHEME] = DEFAULT_PUBLIC_SCHEME
            data[CONF_ACCESS_TOKEN] = data[CONF_ACCESS_TOKEN].strip() or secrets.token_urlsafe(32)
            data[CONF_SETUP_COMPLETE] = True
            self._data = data
            await self.async_set_unique_id(f"{data[CONF_LISTEN_HOST]}:{data[CONF_LISTEN_PORT]}")
            self._abort_if_unique_id_configured()
            return await self.async_step_cli()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LISTEN_PORT, default=DEFAULT_LISTEN_PORT): int,
                    vol.Required(CONF_PUBLIC_HOST, default=_default_public_host(self.hass)): str,
                    vol.Required(CONF_ENDPOINT_PATH, default=DEFAULT_ENDPOINT_PATH): str,
                    vol.Optional(CONF_ACCESS_TOKEN, default=""): str,
                    vol.Required(CONF_TRANSPORT_PREFIX, default=DEFAULT_TRANSPORT_PREFIX): str,
                    vol.Required(CONF_ENABLE_RADIO_PROFILE, default=True): bool,
                    vol.Required(CONF_ENABLE_ACTIVE_BLE, default=DEFAULT_ENABLE_ACTIVE_BLE): bool,
                    vol.Required(CONF_RADIO_PROFILE, default=DEFAULT_RADIO_PROFILE): str,
                }
            ),
        )

    async def async_step_cli(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            return self.async_create_entry(
                title="Aruba BLE Proxy",
                data=self._data,
            )

        return self.async_show_form(
            step_id="cli",
            data_schema=vol.Schema({}),
            description_placeholders={
                "endpoint_url": _endpoint_url(self._data),
                "profile_count": str(_cli_profile_count()),
                "filter_count": str(_cli_filter_count()),
                "cli_config": _generate_cli(self._data),
                "cleanup_cli_config": _generate_cleanup_cli(self._data),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return ArubaBleProxyOptionsFlow()


class ArubaBleProxyOptionsFlow(config_entries.OptionsFlow):
    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    async def async_step_init(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            data = _data_with_defaults(dict(self.config_entry.data))
            data.update(dict(user_input))
            data[CONF_LISTEN_HOST] = DEFAULT_LISTEN_HOST
            data[CONF_PUBLIC_SCHEME] = DEFAULT_PUBLIC_SCHEME
            data[CONF_ENDPOINT_PATH] = _clean_path(str(data[CONF_ENDPOINT_PATH]))
            data[CONF_ACCESS_TOKEN] = str(data[CONF_ACCESS_TOKEN]).strip() or secrets.token_urlsafe(32)
            data[CONF_SETUP_COMPLETE] = True
            self._data = data
            return await self.async_step_cli()

        data = _data_with_defaults(dict(self.config_entry.data))
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_LISTEN_PORT, default=data[CONF_LISTEN_PORT]): int,
                    vol.Required(CONF_PUBLIC_HOST, default=data[CONF_PUBLIC_HOST]): str,
                    vol.Required(CONF_ENDPOINT_PATH, default=data[CONF_ENDPOINT_PATH]): str,
                    vol.Optional(CONF_ACCESS_TOKEN, default=data[CONF_ACCESS_TOKEN]): str,
                    vol.Required(CONF_TRANSPORT_PREFIX, default=data[CONF_TRANSPORT_PREFIX]): str,
                    vol.Required(CONF_ENABLE_RADIO_PROFILE, default=data[CONF_ENABLE_RADIO_PROFILE]): bool,
                    vol.Required(CONF_ENABLE_ACTIVE_BLE, default=data[CONF_ENABLE_ACTIVE_BLE]): bool,
                    vol.Required(CONF_RADIO_PROFILE, default=data[CONF_RADIO_PROFILE]): str,
                }
            ),
        )

    async def async_step_cli(self, user_input: dict[str, Any] | None = None):
        if user_input is not None:
            self.hass.config_entries.async_update_entry(self.config_entry, data=self._data)
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data={})

        return self.async_show_form(
            step_id="cli",
            data_schema=vol.Schema({}),
            description_placeholders={
                "endpoint_url": _endpoint_url(self._data),
                "profile_count": str(_cli_profile_count()),
                "filter_count": str(_cli_filter_count()),
                "cli_config": _generate_cli(self._data),
                "cleanup_cli_config": _generate_cleanup_cli(self._data),
            },
        )
