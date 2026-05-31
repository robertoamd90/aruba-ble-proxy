# Home Assistant Field Test Runbook

This runbook is for testing candidate `0.3.0b7` on a real Home Assistant
instance with a real Aruba AP.

Do not change active BLE code while running this checklist unless a test exposes
a blocking bug. The point is to collect evidence about the current candidate.

## Test Goal

The field test must answer three questions:

1. Does the passive Aruba BLE path still work with other Bluetooth radios
   disabled?
2. Does Home Assistant treat Aruba APs as real Bluetooth scanner sources?
3. Does active BLE/GATT work well enough for a real integration, especially
   SwitchBot Lock / Lock Pro?

## Before Installing

Record these values:

- Home Assistant version:
- Aruba AP model:
- Aruba Instant / AOS version:
- Aruba AP MAC:
- Home Assistant reachable WebSocket URL:
- Devices available for testing:
  - BTHome sensor:
  - SwitchBot thermometer:
  - SwitchBot Lock / Lock Pro:
  - Any BLE device with readable Battery Service `180F`:

Keep one known passive BLE sensor nearby. It is the regression guard while
active BLE is being tested.

## Install Candidate

Manual install target:

```text
/config/custom_components/aruba_ble_proxy
```

Copy only this repository folder:

```text
custom_components/aruba_ble_proxy
```

Then restart Home Assistant.

Expected result after restart:

- Integration loads without a setup error.
- Version shown in Home Assistant is `0.3.0b7`.
- The integration exposes Aruba APs as Bluetooth scanner sources.
- No Aruba BLE Proxy diagnostic sensors are created.

## Configure Aruba

In Home Assistant, open the integration setup/options flow and copy the generated
Aruba CLI block.

On Aruba CLI:

```text
configure terminal
<paste generated Aruba CLI>
commit apply
show iot transportProfile
show running-config | include iot
```

Expected result:

- Transport profiles point to the Home Assistant WebSocket URL.
- `bleDataForwarding` is `TRUE`.
- `blePeriodicTelemetryDisable` is `TRUE`.
- `iot useTransportProfile ...` exists for each generated transport profile.
- `iot use-radio-profile ...` exists for the generated radio profile.

If DNS is used, prove it from the Aruba CLI:

```text
ping ha.example.local
```

Use the hostname that resolves to the Home Assistant LAN address reachable from
the Aruba AP management path.

## Test 1: Passive Regression

Disable or physically remove other Bluetooth paths:

- ESPHome BLE Proxy
- USB/Built-in host Bluetooth passed into Home Assistant
- Other known Bluetooth proxies

Pass criteria:

- Home Assistant Bluetooth advertisements page shows the Aruba AP MAC as source.
- BTHome or SwitchBot thermometer entities continue updating.
- Disabling the Aruba BLE Proxy integration stops those Aruba-sourced updates.
- Re-enabling the integration restores those updates.

Fail evidence to collect:

- Home Assistant log lines from `custom_components.aruba_ble_proxy`.
- Screenshot of Bluetooth advertisements page grouped by source.
- Aruba `show iot transportProfile` output.

## Test 2: Active Scanner Registration

Pass criteria:

- Bluetooth graph shows Aruba AP source nodes connected to observed BLE devices.
- No startup warning says Home Assistant is blocked by the Aruba receiver task.
- `Receiver last peer` shows the Aruba AP connection, not `unknown`.

Fail evidence to collect:

- Home Assistant startup log around `aruba_ble_proxy`.
- Screenshot of the Bluetooth graph.
- Screenshot of the Bluetooth advertisements page grouped by source.

## Test 3: Manual Active GATT Smoke Test

Use Developer Tools -> Actions.

First connect:

```yaml
action: aruba_ble_proxy.ble_connect
data:
  ap_mac: "02:00:00:00:00:01"
  device_mac: "AA:BB:CC:DD:EE:FF"
  timeout: 20
  wait_result: true
```

Expected success shape:

```yaml
sent: true
result:
  received: true
  status: success
```

Then read a known readable characteristic. Battery Level is a good candidate if
the device exposes it:

```yaml
action: aruba_ble_proxy.gatt_read
data:
  ap_mac: "02:00:00:00:00:01"
  device_mac: "AA:BB:CC:DD:EE:FF"
  service_uuid: "0000180f-0000-1000-8000-00805f9b34fb"
  characteristic_uuid: "00002a19-0000-1000-8000-00805f9b34fb"
  timeout: 20
  wait_result: true
```

Expected success shape:

```yaml
sent: true
result:
  received: true
  status: success
characteristic:
  value: "<hex bytes>"
```

Finally disconnect:

```yaml
action: aruba_ble_proxy.ble_disconnect
data:
  ap_mac: "02:00:00:00:00:01"
  device_mac: "AA:BB:CC:DD:EE:FF"
  timeout: 20
  wait_result: true
```

Accepted disconnect statuses:

- `success`
- `notConnected`
- `deviceDisconnected`
- `inactivityTimeout`
- `sourceDisconnected`

After disconnect, pass criteria:

- The HA service call completes without a traceback.
- No new `custom_components.aruba_ble_proxy` error is logged.
- Passive BLE updates continue after the active test.

## Test 4: SwitchBot Lock / Lock Pro

Run this only after passive and manual active smoke tests are clean.

Pass criteria:

- SwitchBot integration can discover or set up the lock with Aruba BLE Proxy as
  the only Bluetooth path.
- The lock no longer fails with `Could not find Switchbot lock_pro` while Aruba
  advertisements are visible.
- A safe command path either works or reaches a clear SwitchBot authentication
  failure after connecting.
- Failed commands do not leave active counters stuck above zero.
- Passive SwitchBot thermometer or BTHome updates continue during the test.

Fail evidence to collect:

- Home Assistant log lines containing `switchbot`, `bleak`, `bluetooth`, and
  `aruba_ble_proxy`.
- Aruba BLE Proxy diagnostic entity values after the failure.
- Whether the failure is discovery, connect, notify, write, read, or disconnect.

## Stop And Report Conditions

Stop the test and collect evidence if:

- Aruba AP disconnects from the WebSocket when an active command is sent.
- Home Assistant reports startup blocked by the Aruba receiver task.
- Any active pending counter stays non-zero after disconnect.
- Passive sensors stop updating during active BLE testing.
- SwitchBot fails repeatedly at the same step.

## Minimal Result Report

Use [FIELD_TEST_REPORT_TEMPLATE.md](FIELD_TEST_REPORT_TEMPLATE.md) after
testing. Minimal summary:

```text
Candidate: 0.3.0b7
HA version:
Aruba model/version:
AP MAC:
Passive regression: pass/fail
Scanner registration: pass/fail
Manual ble_connect: pass/fail/status
Manual gatt_read: pass/fail/status/value
Manual ble_disconnect: pass/fail/status
SwitchBot Lock setup: pass/fail/error
SwitchBot command: pass/fail/error
Counters stuck after test: yes/no
Other Bluetooth radios disabled: yes/no
Logs/screenshots:
```
