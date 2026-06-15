from __future__ import annotations

from typing import Any

from .const import CONF_ACCESS_TOKEN, CONF_ENTRY_TYPE, DOMAIN, ENTRY_TYPE_AP_SOURCE


async def async_get_config_entry_diagnostics(hass, entry) -> dict[str, Any]:
    redacted_data = dict(entry.data)
    if CONF_ACCESS_TOKEN in redacted_data:
        redacted_data[CONF_ACCESS_TOKEN] = "***redacted***"

    payload: dict[str, Any] = {
        "domain": DOMAIN,
        "entry": redacted_data,
        "options": dict(entry.options),
    }
    if entry.data.get(CONF_ENTRY_TYPE) == ENTRY_TYPE_AP_SOURCE:
        payload["runtime"] = None
        return payload

    runtime = getattr(entry, "runtime_data", None)
    if runtime is None:
        payload["runtime"] = None
        return payload

    runtime_payload = dict(runtime.diagnostic_attributes())
    runtime_payload["receiver_connected_sources"] = sorted(
        runtime_payload.get("receiver_connected_sources", [])
    )
    payload["runtime"] = runtime_payload
    return payload

