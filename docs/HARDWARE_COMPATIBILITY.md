# Hardware Compatibility

This document collects community-reported hardware and firmware combinations tested with Aruba BLE Proxy.

These are per-combination reports, not a complete list of supported hardware.
Active GATT has also been exercised in maintainer field testing, but those results
have not yet been recorded here with a complete model/firmware/device combination.
The entries below retain their original reported scope.

| Device | Firmware / Platform | Deployment Mode | Passive BLE | Active BLE / GATT | Tested By | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| Aruba AP-505 | Aruba Instant 8.12.0.3_91078 | Instant | Confirmed in Home Assistant Bluetooth dashboard | Not tested | [Reddit comment](https://www.reddit.com/r/homeassistant/comments/1tsnc33/comment/op02h6h/) | BLE advertisements visible in Home Assistant. |
| Aruba AP-535 | Aruba Instant 8.12.0.3_91078 | Instant | Confirmed in Home Assistant Bluetooth dashboard | Not tested | [Reddit comment](https://www.reddit.com/r/homeassistant/comments/1tsnc33/comment/op02h6h/) | BLE advertisements visible in Home Assistant. |
| Aruba AP-515 | ArubaOS 8.12 | Mobility Gateway | Reported, not yet confirmed | Not tested | [Reddit comment](https://www.reddit.com/r/homeassistant/comments/1tsnc33/comment/oownz81/) | Reported using AP-515 with AOS 8.12 and a Mobility Gateway; functional BLE results were not reported. |
| Aruba AP-515 | Aruba Instant 8.13.3.0_96306 LSR | Instant | Confirmed | Confirmed with SwitchBot Lock Pro | Maintainer field test | Home Assistant uses only Aruba APs for Bluetooth; lock/unlock control confirms an active BLE connection path. |
| Aruba AP-365 | Unknown | Unknown | Reported working | Not tested | [Reddit comment](https://www.reddit.com/r/homeassistant/comments/1tsnc33/comment/op2nfo2/) | Firmware and deployment mode still need confirmation. |
| Aruba AP-345 | Aruba Instant 8.10.0.21_94501 LSR | Instant | Confirmed with live sensor data | Not tested | [GitHub issue #9](https://github.com/robertoamd90/aruba-ble-proxy/issues/9) | 5 APs tested; passive BLE visible in Home Assistant and used with Bermuda BLE Trilateration. Custom filtering not yet tested. |

## Reporting new results

Please include:

- AP model
- firmware version
- deployment mode, such as Instant or controller-managed
- whether passive BLE advertisements are visible in Home Assistant
- whether active BLE/GATT was tested
- any custom Aruba filters that were required
