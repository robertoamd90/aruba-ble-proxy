# Manual Home Assistant Install

This is the current development install path before HACS packaging exists.

## Files to copy

Copy the integration directory into the Home Assistant config directory:

```text
<ha-config>/custom_components/aruba_ble_proxy
```

Example from this repository:

```bash
cp -R custom_components/aruba_ble_proxy /config/custom_components/
```

The helper script does the same copy and also removes the older development-only
`/config/aruba_ble_proxy` folder if it exists:

```bash
scripts/install-ha-manual.sh /config
```

Restart Home Assistant after copying the files.

## Add integration

In Home Assistant:

```text
Settings -> Devices & services -> Add Integration -> Aruba BLE Proxy
```

Recommended defaults:

```text
Listen port: 7443
Endpoint path: /aruba-ble-proxy
Transport profile prefix: ha-ble
Generate Aruba IoT radio profile: enabled
Radio profile: ha-ble-radio
```

Set `Home Assistant host/IP reachable by Aruba APs` to the IP or hostname the APs can reach.
Prefer an internal LAN hostname or IP. Do not use a public/VPN hostname unless the AP can actually
route to that address and port.

If `Access token` is left empty, the integration generates one.

## Aruba configuration

The config flow displays a complete Aruba Instant CLI block.
Copy it into the Aruba CLI and commit it.

The integration also displays a cleanup block that removes the generated Aruba profiles.
Keep that cleanup block somewhere safe during testing. It removes the generated transport profiles and
the generated radio profile in the correct order.

## Validation

After Aruba commits the config:

- Aruba APs should appear as Bluetooth sources in Home Assistant.
- Home Assistant's Bluetooth advertisements page should show Aruba APs as sources.
- supported Home Assistant Bluetooth integrations should start seeing matching devices

Validated so far:

- BTHome events via Aruba BLE Data
- SwitchBot thermometer advertisements

Experimental active BLE work in the local development build:

- Aruba APs are registered as connectable Home Assistant Bluetooth scanner sources
- connect, disconnect, GATT read/write, and notification actions are wired through
  Aruba's southbound action protocol
- one active connection slot is exposed per Aruba AP until concurrent GATT
  sessions are validated on real hardware
- GATT reads, characteristic discovery waits, and notification callbacks are
  scoped by Aruba AP source for multi-AP setups
- SwitchBot `FD3D` devices get a narrow command-service fallback for PySwitchbot

Still requiring real Home Assistant validation before a stable release:

- SwitchBot Lock/Lock Pro active commands
- pairing/bonding workflows
- long-running reconnect, timeout, and AP disconnect behavior

## Current limitation

This integration is not yet packaged for HACS. Manual install currently means copying
`custom_components/aruba_ble_proxy` into Home Assistant and restarting.
