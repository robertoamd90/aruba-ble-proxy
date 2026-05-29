# Aruba BLE Proxy for Home Assistant - Spec v0.1

## Goal

Allow Home Assistant to use Aruba access points as passive remote Bluetooth Low Energy scanners.

The integration must forward raw BLE advertisements from Aruba APs into the Home Assistant Bluetooth stack so existing Home Assistant integrations can decode supported devices.

## Non-Goals for MVP

- No MQTT transport.
- No device-specific decoders.
- No iBeacon, BTHome, Xiaomi, Shelly, SwitchBot, or vendor-specific parsing in this project.
- No device deduplication by MAC/address in this project.
- No AP best-source selection in this project.
- No active BLE/GATT support in the first version.
- No required external bridge, container, or extra local machine.

## Architecture

```text
Aruba AP(s)
  -> WebSocket listener on dedicated Home Assistant port
  -> Aruba protobuf decoder
  -> BLE advertisement normalizer
  -> Home Assistant Bluetooth scanner API
  -> Existing Home Assistant Bluetooth integrations
```

## Home Assistant Behavior

- A single custom integration named `Aruba BLE Proxy`.
- A dedicated WebSocket listener, default port `7443`, configurable.
- A single integration configuration entry.
- A generated or user-provided access token.
- Aruba APs are discovered automatically when they connect.
- Every Aruba `reporter.mac` is treated as a separate Bluetooth scanner source.
- BLE advertisements are passed through without semantic device interpretation.

## Aruba Behavior

The user configures an Aruba IoT Transport Profile pointing to Home Assistant:

```text
ws://<home-assistant-ip>:7443/
```

The Aruba side must be configured to forward raw BLE advertisement data for the relevant device classes. The exact Aruba UI/CLI steps need validation with real hardware and firmware.

## Security

- No token in the URL path or query string.
- Validate `Telemetry.meta.access_token` from the Aruba protobuf payload.
- Use constant-time token comparison.
- Never log token values.
- If no token is configured, run in explicitly insecure mode and log that state.
- Optional future controls:
  - IP/subnet allowlist for APs.
  - TLS / `wss://`.
  - token rotation.
  - rate limiting failed connections.

## Passive MVP

The first phase proves that Aruba BLE data can be received, decoded, normalized, and later injected into Home Assistant.

Required behavior:

1. Accept WebSocket connections from one or more Aruba APs.
2. Decode Aruba telemetry protobuf frames.
3. Extract `Reporter` data:
   - AP name
   - AP MAC
   - AP IP
   - hardware type
   - software version
4. Extract `BleData` data:
   - device MAC
   - frame type
   - raw advertisement payload
   - RSSI
   - address type
   - APB MAC, if present
5. Parse BLE advertising data only into generic AD structures:
   - local name
   - service UUIDs
   - manufacturer data
   - service data
6. Preserve unknown AD structures without failing.
7. Emit one normalized event per Aruba BLE frame.

## Home Assistant MVP

After the standalone receiver works with real AP traffic:

1. Create a custom integration. Implemented initially under `custom_components/aruba_ble_proxy`.
2. Start the dedicated WebSocket listener inside Home Assistant. Implemented; requires HA runtime test.
3. Register external passive Bluetooth scanner sources via Home Assistant Bluetooth APIs. Current implementation forwards `BluetoothServiceInfoBleak` via `async_get_advertisement_callback`; scanner source registration still needs HA runtime validation.
4. Convert normalized events into `BluetoothServiceInfoBleak`. Implemented.
5. Validate with already-supported BLE devices. Pending real HA test.

## Active BLE Future

Active BLE/GATT support is explicitly out of scope for MVP, but the architecture should not block it.

Aruba exposes a Southbound API for:

- BLE connect/disconnect.
- GATT read/write.
- GATT notifications/indications.
- authentication/encryption/bonding.

Future work may introduce an active BLE client layer, but only after passive scanner behavior is proven and stable.

## Open Questions

- Does every target Aruba firmware populate `Telemetry.meta.access_token`?
- Does Aruba expose any supported configuration for generic raw BLE forwarding? Initial AP-515 / AOS 8.13 tests and external Aruba IoT guide notes suggest BLE Data Forwarding is limited to known BLE vendor classes or explicit filters, not `all` / `unclassified`.
- Does Aruba forward enough scan response data for Home Assistant integrations that rely on it?
- Should scan response be emitted as independent observations or merged with advertisements before passing to Home Assistant?
- What is the minimal correct `BluetoothServiceInfoBleak` payload for a passive external scanner?
- How should Home Assistant diagnostics expose AP connection status without overwhelming users?

## Milestones

1. Write project specification.
2. Build standalone Aruba WebSocket receiver and BLE normalizer.
3. Validate with captured Aruba traffic.
4. Build minimal Home Assistant custom integration.
5. Register/forward passive scanner sources in Home Assistant.
6. Test with real BLE devices already supported by Home Assistant.
7. Add diagnostics, configuration flow, and security hardening.
