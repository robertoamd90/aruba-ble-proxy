# Aruba Setup Notes

These notes document the first working Aruba configuration tested against the standalone receiver.

## Receiver

Run the local receiver:

```bash
.venv312/bin/aruba-ble-proxy-receiver --host 0.0.0.0 --port 7443 --log-level debug
```

For the first test, the receiver accepted messages without token validation. The Aruba UI still required a token value.

## Aruba IoT Transport

Create an IoT transport:

```text
Name: test
Enabled: Yes
Server type: Telemetry Websocket
Server URL: ws://<receiver-ip>:7443/test
Authentication method: Token
Access token: example-access-token
Cipher list: Standard
Services: BLE Telemetry, BLE Data
```

The first working receiver IP was:

```text
ws://192.0.2.10:7443/test
```

## Aruba IoT Radio

Create an IoT radio:

```text
Name: test
State: Enabled
Radio: Internal
Radio mode: Scanning
Console: Off
Tx power: 0
```

`Tx power` was required by the Aruba UI even for scanning mode. `0 dBm` was accepted.

## BLE Data Filter

The UI did not expose a generic `Raw BLE Data` or `Unclassified` option in the tested firmware.

The first successful BLE data forwarding used a Service UUID filter:

```text
BLE Data -> Filters -> Service UUID: FCD2
```

This produced `Telemetry.bleData` messages with BTHome service data:

```text
topic=bleData
bleData=1
service_data=['0000fcd2-0000-1000-8000-00805f9b34fb']
```

Two APs reported the same BLE address with different RSSI values, as expected for passive multi-scanner behavior.

## CLI Payload Content Tests

The tested Instant AP CLI saved these payload settings successfully, but they did not forward the tested BTHome/FCD2 device without an explicit `serviceUUIDFilter`:

```text
PayloadContent: all
PayloadContent: all,unclassified
PayloadContent: unclassified
```

In all three cases, with empty filters, the receiver only observed:

```text
topic=apHealthUpdate
bleData=0
```

Known-good baseline remains:

```text
PayloadContent:
bleDataForwarding: TRUE
blePeriodicTelemetryDisable: TRUE
serviceUUIDFilter: FCD2
```

`BLE Telemetry` is not required for BLE advertisement forwarding. `BLE Data` alone continued to produce `Telemetry.bleData` when `serviceUUIDFilter=FCD2` was configured.

The AP accepted a maximum of 10 values in `serviceUUIDFilter`. A 10-value test filter was accepted:

```text
serviceUUIDFilter: FCD2,FE95,FD3D,FD50,FEE5,181C,181E,181B,181D,1801
```

This produced a high volume of BLE Data frames, including:

```text
service_data: 0000fd3d-0000-1000-8000-00805f9b34fb
service_data: 0000fe95-0000-1000-8000-00805f9b34fb
manufacturer_data company id: 2409
local_name: LYWSD03MMC
```

Multiple transport profiles can point to the same WebSocket endpoint. This was validated with `test`
and `test2`, both attached via `iot useTransportProfile`, and both reporting to:

```text
ws://192.0.2.10:7443/test
```

Generate repeatable Aruba CLI for this pattern with:

```bash
.venv312/bin/aruba-ble-proxy-generate-aruba-cli \
  --endpoint-url ws://192.0.2.10:7443/test \
  --token example-access-token
```

The generator chunks `custom_components/aruba_ble_proxy/data/ha_service_uuids_seed.txt` into
transport profiles with at most 10 service UUID filters each.

By default the generator also creates and enables a BLE scanning radio profile:

```text
iot radio-profile ha-ble-radio
radio-instance internal
radio-mode ble
ble-opmode scanning
ble-console off
ble-txpower 0
exit
iot use-radio-profile ha-ble-radio
```

Use `--no-radio-profile` only when the radio profile already exists and should not be touched.

Generate cleanup commands with:

```bash
.venv312/bin/aruba-ble-proxy-generate-aruba-cli --cleanup
```

## External Guide Finding

The FluegelsApps Aruba IoT configuration guide matches the behavior observed in testing:

- BLE data forwarding sends advertisement and scan response frames from **known BLE vendor device classes**.
- Starting with ArubaOS/Instant 8.8, BLE data forwarding is supported for all known BLE vendor classes **except** the special classes `all` and `unclassified`.
- The `all` and `unclassified` classes enable BLE telemetry reporting, not generic BLE data forwarding.
- `perFrameFiltering` is only a modifier for already eligible known device classes; it does not make `all` or `unclassified` behave as raw catch-all BLE forwarding.

Reference:

- https://github.com/FluegelsApps/iot-utilities/blob/main/docs/aruba/aruba_iot_configuration_guide.md#ble-device-class-filter

Practical implication for this project:

- A universal Home Assistant BLE proxy based only on Aruba BLE Data Forwarding is not currently proven feasible.
- Aruba can forward raw BLE payloads for explicit known classes or explicit content filters such as `serviceUUIDFilter=FCD2`.
- Without Aruba support for raw/all advertisement forwarding, this project cannot behave like an ESPHome Bluetooth Proxy for arbitrary BLE devices.
