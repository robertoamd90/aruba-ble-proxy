# Active BLE Test Candidate

This file freezes the current development direction for field testing. It is not
a stable 1.0 definition yet; it is the checklist used to decide whether active
BLE can become stable.

Current candidate version: `0.3.0b3`

## What Is Frozen For This Candidate

The candidate keeps the passive path and enables the experimental active BLE
connector by default:

```text
Aruba AP -> Telemetry WebSocket -> Home Assistant Bluetooth scanner
Aruba AP <- southbound BLE/GATT actions <- Home Assistant Bleak client
```

The intended behavior for this candidate is:

- Aruba APs appear as Home Assistant Bluetooth scanner sources.
- Passive advertisements continue to reach Home Assistant integrations.
- Home Assistant can attempt active GATT through the Aruba AP source.
- Only one active BLE connection per Aruba AP is allowed.
- Active operations are serialized per Aruba AP.
- GATT state, notifications, and characteristic waits are scoped by Aruba AP and
  BLE device.
- SwitchBot `FD3D` devices get the narrow PySwitchbot command-service fallback
  when Aruba does not publish a characteristic list.

No further active BLE behavior should be added before field testing this
candidate unless a test exposes a blocking bug.

## What Local Tests Prove

The Python tests prove only integration-side behavior:

- Aruba protobuf action messages are encoded and decoded correctly enough for
  the implemented paths.
- Runtime state tracks pending actions, disconnects, notification callbacks,
  AP-source scoping, and one-slot-per-AP guards.
- The custom Bleak client maps Home Assistant operations to Aruba actions.
- Failure paths such as timeouts, disconnects, duplicated connects, and callback
  errors do not leave obvious stale local state.
- The CLI generator and service schemas remain syntactically valid.

Local tests do **not** prove that an Aruba AP firmware accepts every southbound
action or that a commercial BLE integration such as SwitchBot Lock will complete
its real command flow.

## What Home Assistant Field Tests Must Prove

These tests need a real Home Assistant instance and at least one Aruba AP.
Use [HA_FIELD_TEST_RUNBOOK.md](HA_FIELD_TEST_RUNBOOK.md) as the operational
checklist for the current candidate.

### Passive Regression

Pass criteria:

- Aruba AP connects to the WebSocket receiver.
- `BLE advertisements` increases.
- Home Assistant's Bluetooth advertisements page shows Aruba AP MACs as sources.
- BTHome or SwitchBot thermometer updates continue with other Bluetooth radios
  disabled.

This proves the stable passive use case did not regress.

### Active Scanner Registration

Pass criteria:

- Aruba AP appears in Home Assistant as a Bluetooth source.
- The Bluetooth graph shows Aruba AP sources linked to observed BLE devices.
- No Home Assistant startup warning remains caused by the Aruba receiver task.
- Removing or disabling the integration stops updates from Aruba-sourced BLE
  devices.

This proves Home Assistant is really using the integration as a Bluetooth
scanner source.

### Active GATT Smoke Test

Pass criteria:

- `aruba_ble_proxy.ble_connect` succeeds against a known nearby device.
- `aruba_ble_proxy.gatt_read` succeeds against a known readable characteristic,
  such as Battery Service `180F` / Battery Level `2A19`, if the device exposes
  it.
- `aruba_ble_proxy.ble_disconnect` succeeds or returns an accepted idempotent
  disconnect status.
- Diagnostic entities do not show growing pending actions, characteristic
  waits, or notification subscriptions after disconnect.

This proves the Aruba AP accepts the basic active BLE command path.

### SwitchBot Lock / Lock Pro Test

Pass criteria:

- Home Assistant discovers or configures the SwitchBot lock while Aruba BLE
  Proxy is the only available Bluetooth path.
- The lock integration can connect through the Aruba AP.
- At least one safe command path works or reaches the expected SwitchBot-level
  authentication failure.
- Failed commands do not leave the Aruba AP stuck with an active connection.
- Passive thermometer/BTHome updates still continue while testing the lock.

This is the decisive test for whether active BLE is useful beyond diagnostics.

## Definition Of Stable 1.0

Version 1.0 should not mean "all BLE devices work". It should mean the project
has a reliable, documented contract.

Minimum 1.0 criteria:

- Passive BLE forwarding is stable and remains the primary supported feature.
- Aruba AP scanner registration works consistently in Home Assistant.
- Active BLE can be enabled or disabled from options without reinstalling.
- Active GATT either works for at least one real supported workflow or is clearly
  labeled experimental and disabled by default.
- The one-active-connection-per-AP limit is documented and enforced.
- Startup, unload, reload, and receiver disconnects clean up tasks and local
  state.
- Diagnostics expose enough state to troubleshoot failed active operations.
- Manual install and Aruba CLI generation docs are current.
- The repository has no required uncommitted vendor checkout for normal tests or
  manual installation.

If SwitchBot Lock works reliably through Home Assistant, active BLE can be part
of the 1.0 supported surface with the documented AP slot limit. If it does not,
1.0 should keep active BLE experimental or disabled by default instead of
pretending to be a complete BLE proxy replacement.

## Stop Conditions During Field Testing

Stop and collect logs before changing code if any of these happen:

- Aruba WebSocket disconnects when an active command is sent.
- Home Assistant startup is blocked by the receiver task.
- `active_operations_in_flight` or pending counters remain non-zero after a
  failed operation and disconnect.
- A second passive device stops updating while testing an active connection.
- SwitchBot commands fail with a stable, repeated Aruba status that is not
  currently mapped by the integration.
