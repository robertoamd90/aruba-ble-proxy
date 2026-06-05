# Aruba BLE Proxy for Home Assistant - Spec v1.0

## Goal

Allow Home Assistant to use Aruba access points as Bluetooth Low Energy scanner
sources.

The integration forwards BLE advertisements from Aruba APs into the Home
Assistant Bluetooth stack and exposes an Aruba-backed active BLE/GATT connector
for integrations that use Bleak.

```text
Aruba AP(s)
  -> WebSocket listener on Home Assistant
  -> Aruba protobuf decoder
  -> BLE advertisement normalizer
  -> Home Assistant Bluetooth scanner API
  -> Existing Home Assistant Bluetooth integrations

Home Assistant Bleak client
  -> Aruba southbound BLE/GATT action
  -> Aruba AP
  -> BLE peripheral
```

## Supported Surface

- WebSocket receiver for one or more Aruba APs.
- Aruba protobuf decoding for BLE Data, GATT characteristics, action results,
  and device status updates.
- Passive BLE advertisement forwarding into Home Assistant Bluetooth.
- Per-AP Home Assistant Bluetooth scanner registration when supported by the
  running Home Assistant version.
- Active BLE connect/disconnect through Aruba southbound actions.
- GATT read/write and notification enable/disable through Aruba southbound
  actions.
- Active connection slots per Aruba AP, configurable from integration options.
- GATT state, characteristic waits, notification callbacks, and connected-device
  state scoped by Aruba AP source and BLE device.
- Narrow SwitchBot command-service fallback for devices advertising service UUID
  `FD3D` when Aruba does not report the known command characteristics.
- Manual services for diagnostics and direct action testing:
  - `aruba_ble_proxy.ble_connect`
  - `aruba_ble_proxy.ble_disconnect`
  - `aruba_ble_proxy.gatt_read`
  - `aruba_ble_proxy.gatt_write`
  - `aruba_ble_proxy.gatt_notify`

## Non-Goals

- No MQTT transport.
- No device-specific decoders.
- No parsing, decrypting, repairing, or deduplicating application protocols such
  as BTHome, Xiaomi/Mi, Shelly, SwitchBot payload formats, iBeacon, or vendor
  telemetry.
- No generic invention of GATT characteristics when Aruba does not report them.
- No BLE pairing, bonding, unpairing, or descriptor read/write.
- No AP best-source selection policy beyond Home Assistant's Bluetooth behavior
  and the selected Aruba AP source for active connections.
- No required external bridge, container, or extra local machine.

## Home Assistant Behavior

- A single custom integration named `Aruba BLE Proxy`.
- A dedicated WebSocket listener, default port `7443`, configurable.
- A generated or user-provided access token.
- Aruba APs are discovered automatically when they connect.
- Every Aruba `reporter.mac` is treated as a separate Bluetooth scanner source.
- BLE advertisements are passed through without semantic device interpretation.
- Active BLE can be enabled or disabled from integration options.
- Active connection slots per AP are configurable and enforced locally before
  sending new connect actions to Aruba.

## Aruba Behavior

The user configures Aruba IoT profiles pointing to Home Assistant:

```text
ws://<home-assistant-ip>:7443/aruba-ble-proxy
```

Aruba must be configured to forward BLE Data for the desired service UUIDs or
device classes. Aruba firmware and profile behavior decide which advertisements
are sent to the WebSocket endpoint; this project does not make Aruba forward
unfiltered BLE traffic by itself.

## Security

- No token in the URL path or query string.
- Validate `Telemetry.meta.access_token` from the Aruba protobuf payload.
- Use constant-time token comparison.
- Never log token values.
- If no token is configured, run in explicitly insecure mode and log that state.

Potential future controls:

- IP/subnet allowlist for APs.
- TLS / `wss://`.
- token rotation.
- rate limiting failed connections.

## GATT Discovery Contract

When Aruba reports GATT characteristics, the integration builds a normal Bleak
service collection from Aruba's service UUID, characteristic UUID, and property
metadata.

When Aruba does not report a characteristic list, the integration cannot build a
generic service collection from advertising alone. Advertising commonly exposes
service UUIDs but not characteristic UUIDs or properties.

The only built-in exception is the narrow SwitchBot fallback:

- trigger: advertised service UUID `FD3D`
- service: `cba20d00-224d-11e6-9fb8-0002a5d5c51b`
- write characteristic: `cba20002-224d-11e6-9fb8-0002a5d5c51b`
- read/notify characteristic: `cba20003-224d-11e6-9fb8-0002a5d5c51b`

This is a compatibility fallback for known SwitchBot command characteristics,
not a generic Aruba discovery replacement.

## Limits For 1.0

- Active BLE/GATT is supported, but not equivalent to a local host Bluetooth
  adapter or ESPHome Bluetooth Proxy in every edge case.
- Pairing/bonding workflows are not implemented.
- Application payload correctness remains the responsibility of the BLE device
  firmware and the Home Assistant integration that decodes it.
- The proxy does not decrypt encrypted BLE application payloads.
- Aruba characteristic discovery gaps are exposed as missing characteristics
  unless covered by the narrow SwitchBot fallback above.

## Milestones Reached

1. Standalone Aruba WebSocket receiver and BLE normalizer.
2. Home Assistant custom integration and config flow.
3. Aruba CLI generation and cleanup generation.
4. Passive BLE forwarding into Home Assistant Bluetooth.
5. Per-AP scanner registration.
6. Active BLE/GATT action path through Aruba southbound protobufs.
7. Source-scoped active state for multi-AP deployments.
8. Narrow SwitchBot compatibility fallback for incomplete Aruba discovery.
