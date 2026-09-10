# Aruba BLE Proxy

Use your Aruba access points as Bluetooth Low Energy proxies for Home Assistant. Forward supported BLE advertisements and use active GATT connections through your existing APs.

![Aruba BLE Proxy icon](custom_components/aruba_ble_proxy/brand/icon.png)

```text
Aruba AP → WebSocket → Home Assistant Bluetooth → device integrations
```

## Requirements and compatibility

- Home Assistant with the Bluetooth integration available.
- An Aruba AP and firmware supporting IoT BLE scanning and Telemetry WebSocket transport. See the [hardware compatibility table](docs/HARDWARE_COMPATIBILITY.md) for reported combinations.
- Network connectivity from the APs to Home Assistant on the configured listener port (default `7443`). This is separate from the Home Assistant web interface.
- For BLE device discovery, an advertiser matching the Aruba transport filters and a Home Assistant integration supporting that device.

The listener uses plain `ws://`. Keep it on a trusted network and restrict access to the APs. Generated setup commands target Aruba Instant; controller-managed deployments may need configuration adjustments.

## Install with HACS

Add this project as a **custom repository** in [HACS](https://www.hacs.xyz/docs/faq/custom_repositories/):

1. Open HACS, then the three-dot menu → **Custom repositories**.
2. Enter `https://github.com/robertoamd90/aruba-ble-proxy` and select **Integration**.
3. Add the repository, find **Aruba BLE Proxy**, and download the latest stable release.
4. Restart Home Assistant.
5. Open **Settings → Devices & services → Add integration → Aruba BLE Proxy**.

Custom repository installation does not require inclusion in the HACS default catalog. HACS manages installation and updates; you still configure the Aruba APs below.

Already installed manually? Back up your integration directory, add this repository to HACS, and download the release. Keep your existing Home Assistant integration entries and restart; you do not need to delete or recreate them. Downloads may overwrite local changes inside the integration directory.

For installation without HACS, see [manual installation](docs/INSTALL_MANUAL.md). No standalone receiver, development environment or protobuf compilation is required for normal Home Assistant use.

## Configure Aruba

1. In integration setup, enter the Home Assistant LAN address reachable from your APs. Keep port `7443` and path `/aruba-ble-proxy` unless you need different values.
2. Leave the access token empty to generate one, or provide your own.
3. Copy the generated Aruba CLI configuration and apply it using the Aruba CLI.
4. Confirm that the IoT transport profiles connect to the Home Assistant endpoint.

The integration generates a BLE scanning radio profile and transport profiles with service UUID filters, split into groups of at most 10 UUIDs. Setup/options also provide cleanup commands. Review generated commands before applying them to a deployment with existing IoT profiles.

## What to expect

- Each AP appears as a Bluetooth scanner named `Aruba AP <MAC>` after its first telemetry message containing the AP MAC, even without matching BLE advertisements. On firmware sending periodic AP health messages, allow roughly two minutes after connection; timing depends on the AP.
- Previously configured scanners are restored when the integration starts. Their presence alone does not prove the AP is currently connected or forwarding advertisements.
- The first BLE advertisement remains another registration trigger, using the same identity without creating a second scanner.
- The hardware model uses Aruba's `hwType` when available, otherwise `Aruba AP`. A model learned after registration is saved and may need another restart to appear.
- Device integrations receive matching advertisements through Home Assistant Bluetooth. Active BLE supports connect/disconnect, GATT read/write and notifications, with configurable connection slots per AP.

Multiple APs can share a cluster WebSocket connection. Each retains its own scanner identity and active connection routing.

## Troubleshooting

**AP connected, but no BLE devices?** Aruba filters determine which advertisements are forwarded. A connected scanner can legitimately have `events: 0`. Test with a matching advertiser, such as a BTHome device (`FCD2`); a phone beacon does not necessarily match the generated filters.

**AP does not appear?** Check the endpoint address, port, path, token and firewall, then download integration diagnostics from **Settings → Devices & services → Aruba BLE Proxy**. Compare `receiver_connected_sources`, `receiver_binary_messages`, `registered_scanners`, `events` and `bluetooth_forwards`. An established WebSocket alone is not sufficient for first registration.

**Active BLE fails?** Check Home Assistant logs and the device's GATT support. Include AP model, firmware, Home Assistant version, integration version and whether passive advertisements work when [reporting an issue](https://github.com/robertoamd90/aruba-ble-proxy/issues). Remove tokens and private data from logs before sharing.

## Limits

- Aruba filtering means this is not a universal catch-all proxy for every nearby BLE advertisement.
- Pairing/bonding, descriptor read/write and unpairing are not implemented.
- Aruba may return incomplete GATT discovery. A narrow SwitchBot `FD3D` command-service fallback is included; it is not a general repair for device protocols.
- Device decoding belongs to Home Assistant's device integrations. This project does not publish MQTT state.

See the [field-test checklist](docs/HA_FIELD_TEST_RUNBOOK.md), [active BLE technical notes](docs/ACTIVE_BLE_FEASIBILITY.md) and [release notes](https://github.com/robertoamd90/aruba-ble-proxy/releases).

## Development and standalone tools

Clone the repository, create a Python virtual environment, and install development dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

The standalone receiver is installed by that command. It logs decoded traffic; it does not forward advertisements into Home Assistant. Stop the integration first if using the same port:

```bash
aruba-ble-proxy-receiver --host 0.0.0.0 --port 7443 --access-token "your-token" --log-level debug
```

Use `--summary` for compact BLE output. CLI equivalents of configuration and cleanup are available:

```bash
aruba-ble-proxy-generate-aruba-cli --endpoint-url ws://192.0.2.10:7443/aruba-ble-proxy --token "your-token"
aruba-ble-proxy-generate-aruba-cli --cleanup
```

Generated protobuf modules are committed inside the integration. Only developers updating Aruba's protocol definitions need `scripts/generate-aruba-protobuf.sh`; it reads sources from `vendor/aos8-iot-server-example-websocket` by default, with `ARUBA_PROTO_DIR` and `ARUBA_PROTO_OUT` overrides. See [SPEC.md](SPEC.md) for architecture and [historical Aruba setup observations](docs/ARUBA_SETUP.md) for early transport experiments.

## License and affiliation

Licensed under [GNU GPL v3.0](LICENSE). This project is not affiliated with, endorsed by, or sponsored by HPE Aruba Networking. Integration artwork is original; Home Assistant 2026.3 and newer supports the bundled local brand assets.
