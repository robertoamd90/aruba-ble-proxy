# Hardware Compatibility

This document collects community-reported hardware and firmware combinations tested with Aruba BLE Proxy.

| Device | Firmware / Platform | Deployment Mode | Passive BLE | Active BLE / GATT | Tested By | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Aruba AP-505 | Aruba Instant 8.12.0.3_91078 | Instant | Confirmed in Home Assistant Bluetooth dashboard | Not tested | Community report | BLE advertisements visible in Home Assistant. |
| Aruba AP-535 | Aruba Instant 8.12.0.3_91078 | Instant | Confirmed in Home Assistant Bluetooth dashboard | Not tested | Community report | BLE advertisements visible in Home Assistant. |
| Aruba AP-515 | ArubaOS 8.12 | Mobility Gateway | Reported, not yet confirmed | Not tested | Community report | User reported AP-515 with AOS 8.12 and a Mobility Gateway. |
| Aruba AP-365 | Unknown | Unknown | Reported working | Not tested | Community report | Firmware and deployment mode still need confirmation. |

## Reporting new results

Please include:

- AP model
- firmware version
- deployment mode, such as Instant or controller-managed
- whether passive BLE advertisements are visible in Home Assistant
- whether active BLE/GATT was tested
- any custom Aruba filters that were required
