# Active BLE Feasibility

This document defines the boundary between the field-tested passive path and
the experimental active BLE work needed before a stable 1.0 release.

## Current State

The integration currently handles Aruba **BLE Data** forwarding:

```text
Aruba AP -> Telemetry WebSocket -> BLE advertisements -> Home Assistant Bluetooth
```

This is passive scanning. It can help Home Assistant integrations that only need
advertisements, such as BTHome sensors or SwitchBot thermometer advertisements.

It now includes an experimental southbound action path for active BLE/GATT
testing and an experimental Home Assistant Bluetooth connector backed by Aruba
southbound actions.

When supported by the running Home Assistant version, each Aruba AP source is
registered as a remote Bluetooth scanner. With active BLE enabled, the scanner
is connectable and Home Assistant can try GATT operations through that specific
AP. With active BLE disabled, the same scanner remains passive and only forwards
advertisements.

Advertisement `connectable` state is derived from Aruba BLE frame type:
`ADV_IND` and `ADV_DIRECT_IND` are forwarded as connectable, while non-connectable
advertising frames remain passive-only.

## What Active BLE Would Mean

Active BLE support would require Home Assistant to perform operations through an
Aruba AP, such as:

- connect to a BLE peripheral
- discover services and characteristics
- read characteristics
- write characteristics
- subscribe to notifications
- disconnect reliably
- coordinate concurrent operations across APs

This is required by devices such as SwitchBot Lock, which cannot be fully handled
from passive advertisements alone.

## Aruba Southbound Findings

The bundled Aruba protobufs expose southbound BLE actions over the same
Telemetry WebSocket transport:

- `bleConnect`
- `bleDisconnect`
- `gattRead`
- `gattWrite`
- `gattWriteWithResponse`
- `gattNotification`
- `gattIndication`
- `bleAuthenticate`
- `bleEncrypt`

The southbound container is `IotSbMessage` with `meta.sbTopic = actions`,
`receiver.apMac`, and one or more `Action` messages. Aruba returns northbound
`ActionResult` messages and can also return `Characteristic` messages for GATT
data.

The integration has local support for:

- encoding Aruba southbound action protobufs
- tracking AP WebSocket connections by reporter MAC
- sending an action payload back to a connected AP
- decoding northbound action results and characteristics
- registering Aruba AP scanners with an experimental Home Assistant Bluetooth
  connector backed by Aruba southbound actions
- keeping GATT reads, characteristic discovery waits, and notification callbacks
  scoped by AP source so two Aruba APs can see the same device without mixing
  active BLE responses
- exposing manual HA services for field tests:
  - `aruba_ble_proxy.ble_connect`
  - `aruba_ble_proxy.ble_disconnect`
  - `aruba_ble_proxy.gatt_read`
  - `aruba_ble_proxy.gatt_write`
  - `aruba_ble_proxy.gatt_notify`

These services are intentionally low-level. They are for proving Aruba active BLE
behavior on real hardware before building a generic Home Assistant connector.
When `wait_result: false` is used, the service only sends the southbound action
and returns immediately; this includes `gatt_read`, which will not wait for a
later northbound characteristic payload in that mode.

The experimental connector currently maps the first set of Bleak operations to
Aruba actions:

- `connect` -> `bleConnect`
- `disconnect` -> `bleDisconnect`
- `read_gatt_char` -> `gattRead`
- `write_gatt_char` -> `gattWrite` or `gattWriteWithResponse`
- `start_notify` / `stop_notify` -> `gattNotification` with value `01` / `00`

After `connect`, the backend waits briefly for Aruba northbound
`characteristics` messages for the connected device. If Aruba publishes them,
the backend builds a Bleak service collection from those characteristics so Home
Assistant integrations can resolve service/characteristic UUIDs through the
normal Bleak API. If no characteristics arrive, the connection still succeeds
but `client.services` remains empty and the diagnostic counters
`active_characteristic_waits` / `active_characteristic_wait_timeouts` show what
happened.

Descriptor access, pairing, and unpairing are still not implemented in the Bleak
connector. Notifications are experimental because Aruba's public protobufs do
not document the enable/disable value bytes; the current implementation uses
`01` to enable and `00` to disable.

Notification callback failures are isolated: one failed callback is logged and
counted in `active_notification_callback_errors` without preventing other
callbacks for the same characteristic from receiving the update. If disabling a
notification returns a non-success Aruba result, the callback remains registered
locally so state does not drift silently.

If Aruba reports a device disconnect while an active action or GATT read is
waiting, the runtime now fails the pending operation immediately with the
disconnect status instead of waiting for the normal action or characteristic
timeout. A pending `bleDisconnect` is the exception: `deviceDisconnected` and
`notConnected` are treated as successful idempotent disconnect outcomes. The
same applies to `inactivityTimeout` and `sourceDisconnected`: if the device or
AP is already gone while Home Assistant is disconnecting, cleanup should
complete instead of surfacing a false failure.

The connector is enabled by default in the current experimental build so field
tests exercise the active path immediately. It can be disabled from integration
options with `Enable experimental active BLE/GATT connector`; disabling it keeps
the passive Aruba advertisement forwarding path active.

The Home Assistant connector currently exposes one active connection slot per
Aruba AP. This is conservative: it matches the registered scanner slot count and
avoids concurrent GATT sessions on one AP until real hardware testing proves
that multiple active sessions are reliable. The runtime also serializes active
southbound operations per Aruba AP source, including manual service calls, so a
second operation for the same AP waits behind the first even if it targets a
different BLE device. Once a BLE device is connected through an AP, a second
connect for another device on the same AP is rejected locally with
`noMoreConnectionSlots` instead of being sent to Aruba; a duplicate connect for
the already active device returns local `alreadyConnected`.

For multi-AP deployments, active GATT state is keyed by Aruba source AP and BLE
device. If two APs see the same lock or sensor, a GATT read or notification
started through AP A only consumes characteristic updates reported by AP A.

The current client also records advertised service UUIDs per BLE device. If a
device advertises the SwitchBot service UUID `FD3D` and Aruba does not provide a
GATT characteristic discovery result after `bleConnect`, the client exposes the
minimal SwitchBot command service expected by PySwitchbot:

- service `cba20d00-224d-11e6-9fb8-0002a5d5c51b`
- write characteristic `cba20002-224d-11e6-9fb8-0002a5d5c51b`
- read/notify characteristic `cba20003-224d-11e6-9fb8-0002a5d5c51b`

This fallback is intentionally narrow. It is only activated for devices that
advertise `FD3D`, and it should be removed or replaced if Aruba proves to emit a
complete characteristic list reliably.

## Unknowns To Resolve First

Before exposing active BLE as a stable feature, the project needs proof that
Aruba executes these commands reliably in an Instant/IAP setup.

Open questions:

- Are these commands available on Instant/IAP without Aruba Central or vendor
  applications?
- Can commands target a specific AP radio reliably?
- What does the AP return for connection failures, timeouts, pairing errors, and
  busy radio conditions?
- Can multiple active sessions per AP be handled without breaking passive
  forwarding, or should the one-slot limit remain for 1.0?
- Can Home Assistant's Bluetooth stack use the experimental connector reliably
  for real integrations, especially SwitchBot Lock/Lock Pro?
- Does the SwitchBot fallback cover the real command path, or does Aruba require
  additional service discovery/notification behavior?

## Non-goals For The Passive MVP

The passive MVP must not pretend to support:

- generic ESPHome Bluetooth Proxy equivalence
- SwitchBot Lock commands
- BLE pairing/bonding
- arbitrary GATT read/write
- Zigbee/ZHA coordinator behavior

## Proposed Investigation Path

1. Capture Aruba documentation and protobuf messages related to BLE action or
   southbound commands. Done locally from Aruba protobufs and examples.
2. Build a low-level action path in the Home Assistant integration. Initial
   scaffold done.
3. Prove one minimal operation, such as connecting to a known BLE peripheral and
   reading one characteristic.
4. Measure timeout and concurrency behavior with passive scanning still enabled.
5. Only then decide whether the Home Assistant integration should expose active
   BLE through the HA Bluetooth APIs or a narrower custom service.

Until step 3 works on real hardware, active BLE remains a research track, not a
supported feature.

## Field Test Procedure

Use these services from Home Assistant Developer Tools after the AP is connected
and visible as a Bluetooth source. Troubleshooting should use service responses,
Home Assistant logs, and the Bluetooth advertisements page rather than
recorder-backed diagnostic sensors.

First prove connection:

```yaml
action: aruba_ble_proxy.ble_connect
data:
  ap_mac: "02:00:00:00:00:01"
  device_mac: "02:00:00:00:01:01"
  timeout: 20
  wait_result: true
```

Expected response shape:

```yaml
sent: true
action_id: "<generated>"
result:
  received: true
  status: success
```

Then prove a read against a known service/characteristic:

```yaml
action: aruba_ble_proxy.gatt_read
data:
  ap_mac: "02:00:00:00:00:01"
  device_mac: "02:00:00:00:01:01"
  service_uuid: "0000180f-0000-1000-8000-00805f9b34fb"
  characteristic_uuid: "00002a19-0000-1000-8000-00805f9b34fb"
  timeout: 20
  wait_result: true
```

Expected response shape:

```yaml
sent: true
result:
  received: true
  status: success
characteristic:
  received: true
  value: "<hex value>"
```

If `result.status` is not `success`, Aruba is receiving the southbound command
but rejecting or failing the BLE operation. If `result` times out, either the AP
did not execute the action or the action result is not being sent on this ArubaOS
path. If `result` succeeds but `characteristic` times out, the AP accepted the
read action but did not publish the GATT value in a `characteristics` northbound
message.

For manual writes, `aruba_ble_proxy.gatt_write` expects hexadecimal bytes in the
`value` field. Spaces, colons, and dashes are accepted, so these are equivalent:

```yaml
value: "570f4e0101000000"
value: "57 0f 4e 01 01 00 00 00"
value: "57:0f:4e:01:01:00:00:00"
```
