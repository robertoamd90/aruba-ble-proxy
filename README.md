# Aruba BLE Proxy

Experimental Home Assistant integration to use Aruba access points as Bluetooth
Low Energy scanner sources, with passive advertisement forwarding and an
experimental active BLE/GATT connector.

This is not a device decoder and does not publish MQTT state. The intended direction is:

```text
Aruba AP -> WebSocket/protobuf -> Home Assistant Bluetooth stack
```

Current phase: passive path field-tested, active BLE/GATT implemented locally
and awaiting wider real-device validation before 1.0.

This project is not affiliated with, endorsed by, or sponsored by HPE Aruba
Networking. The included integration icon/logo assets are original project
artwork and do not use Aruba trademarks or logos.
Home Assistant 2026.3 and newer can load these local brand assets from the
integration's `brand/` directory.

See [SPEC.md](SPEC.md) for scope and architecture.

## Development

Install dependencies:

```bash
python3 -m pip install -e ".[dev]"
```

The generated Aruba protobuf Python files are committed under
`custom_components/aruba_ble_proxy/proto_generated`, so a fresh clone is enough
for normal development, tests, and manual Home Assistant installation.

Regenerate them only when Aruba's upstream `.proto` files need to be refreshed:

```bash
scripts/generate-aruba-protobuf.sh
```

By default the script expects Aruba's
[`aos8-iot-server-example-websocket`](https://github.com/aruba/aos8-iot-server-example-websocket)
repository under `vendor/aos8-iot-server-example-websocket` and writes generated files into
`custom_components/aruba_ble_proxy/proto_generated`.
The `vendor/` directory is intentionally local-only and is not committed.
You can override paths:

```bash
ARUBA_PROTO_DIR=/path/to/proto_files/source \
ARUBA_PROTO_OUT=custom_components/aruba_ble_proxy/proto_generated \
scripts/generate-aruba-protobuf.sh
```

Run the standalone receiver for local protocol/debug testing:

```bash
aruba-ble-proxy-receiver --host 0.0.0.0 --port 7443 --log-level info
```

The standalone receiver accepts Aruba WebSocket connections, decodes BLE Data
protobuf messages, and logs normalized advertisements. It does not forward
advertisements into Home Assistant; that path is implemented by the custom
integration running inside Home Assistant.

For field testing, compact BLE summaries are easier to read:

```bash
aruba-ble-proxy-receiver --host 0.0.0.0 --port 7443 --log-level info --summary
```

If an Aruba access token is configured:

```bash
aruba-ble-proxy-receiver --access-token "secret"
```

The CLI also reads environment variables:

```bash
ARUBA_BLE_PROXY_HOST=0.0.0.0
ARUBA_BLE_PROXY_PORT=7443
ARUBA_BLE_PROXY_ACCESS_TOKEN=secret
ARUBA_BLE_PROXY_LOG_LEVEL=info
ARUBA_BLE_PROXY_SUMMARY=true
```

Command line flags override environment variables.

## Aruba CLI filter generation

Aruba Instant accepted at most 10 `serviceUUIDFilter` values per transport profile in local testing.
The generator emits a complete Aruba Instant CLI block:

- one BLE scanning IoT radio profile
- multiple BLE Data transport profiles
- one `serviceUUIDFilter` chunk per transport profile, with at most 10 UUIDs per chunk

Generate the CLI block:

```bash
aruba-ble-proxy-generate-aruba-cli \
  --endpoint-url ws://192.0.2.10:7443/test \
  --token example-access-token
```

Write it to a file instead of stdout:

```bash
aruba-ble-proxy-generate-aruba-cli \
  --endpoint-url ws://192.0.2.10:7443/test \
  --token example-access-token \
  --output aruba-ha-ble-config.txt
```

The default seed file is `custom_components/aruba_ble_proxy/data/ha_service_uuids_seed.txt`.
This is a practical compatibility list, not a universal BLE catch-all.

Generate cleanup commands for the same generated profiles:

```bash
aruba-ble-proxy-generate-aruba-cli --cleanup
```

## Home Assistant custom integration

The initial custom integration lives under:

```text
custom_components/aruba_ble_proxy
```

Implemented locally:

- config flow with endpoint, token, and Aruba profile settings
- generated Aruba CLI block during setup and options flow
- `aruba_ble_proxy.generate_cli` service with response data
- WebSocket receiver lifecycle inside Home Assistant
- Aruba BLE advertisements converted to `BluetoothServiceInfoBleak`
- Aruba APs registered as passive Home Assistant Bluetooth scanner sources when supported by HA
- forwarding into Home Assistant Bluetooth via `async_get_advertisement_callback`
- no recorder-backed diagnostic sensors; validation is done through Home Assistant Bluetooth sources and logs
- experimental connectable Home Assistant Bluetooth scanner support for active BLE/GATT
- experimental Aruba BLE action path for connect, disconnect, GATT read/write, and notifications
- active BLE connection slots per AP are configurable
- active GATT reads, characteristic discovery, and notifications are scoped by Aruba AP source
- SwitchBot command service fallback when a device advertises SwitchBot service UUID `FD3D`
- passive BLE validated with BTHome and SwitchBot thermometer advertisements

Validated in a real Home Assistant setup:

- Aruba AP connects to the integration over WebSocket
- Aruba BLE Data advertisements are forwarded into Home Assistant Bluetooth
- BTHome events continue working with ESPHome BLE proxy and host Bluetooth disabled
- SwitchBot thermometer advertisements work through the passive path

Known limitation before 1.0:

- active BLE/GATT is implemented locally but still needs real Home Assistant
  validation with devices such as SwitchBot Lock before it can be considered stable

Active BLE feasibility notes are tracked in
[docs/ACTIVE_BLE_FEASIBILITY.md](docs/ACTIVE_BLE_FEASIBILITY.md).
The current field-test candidate and 1.0 criteria are tracked in
[docs/ACTIVE_BLE_TEST_CANDIDATE.md](docs/ACTIVE_BLE_TEST_CANDIDATE.md).
The Home Assistant field-test checklist is in
[docs/HA_FIELD_TEST_RUNBOOK.md](docs/HA_FIELD_TEST_RUNBOOK.md).
Use [docs/FIELD_TEST_REPORT_TEMPLATE.md](docs/FIELD_TEST_REPORT_TEMPLATE.md)
to record test results before changing active BLE behavior again.

Manual install instructions are in [docs/INSTALL_MANUAL.md](docs/INSTALL_MANUAL.md). The install
requires copying only `custom_components/aruba_ble_proxy`.

## Hardware Compatibility

Community-tested hardware and firmware combinations are tracked in
[docs/HARDWARE_COMPATIBILITY.md](docs/HARDWARE_COMPATIBILITY.md).

## License

This project is licensed under the **GNU General Public License v3.0**. See [LICENSE](LICENSE).