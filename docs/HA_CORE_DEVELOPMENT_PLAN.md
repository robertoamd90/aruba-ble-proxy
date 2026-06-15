# Home Assistant Core Development Plan

This document is the implementation plan for making Aruba BLE Proxy ready for a
possible Home Assistant Core submission.

The current 1.0 release is a valid HACS/custom integration target. Core
submission has stricter constraints: smaller review surface, library separation,
Home Assistant quality scale rules, official docs, and stronger tests.

## Non-Negotiable Product Decisions

- Active BLE/GATT stays in scope.
- The core candidate must keep connect, disconnect, GATT read, GATT write, and
  notification support.
- Vendor-specific compatibility behavior must not be hidden inside the generic
  GATT client logic.
- Compatibility behavior must be isolated in structured override data and
  applied by a generic override engine.
- The proxy must not decode, repair, or reinterpret application payloads such as
  BTHome, Xiaomi, Shelly, or SwitchBot payloads.
- Advertisement deduplication and application-level counter handling stay out of
  the proxy unless a future requirement is backed by a protocol-level reason.

## Home Assistant Core References

Use the current official Home Assistant developer documentation as the source of
truth while implementing:

- Contributing an integration to core:
  https://developers.home-assistant.io/docs/core/integration/contributing_to_core/
- Integration quality scale:
  https://developers.home-assistant.io/docs/core/integration-quality-scale/
- Quality scale rules:
  https://developers.home-assistant.io/docs/core/integration-quality-scale/rules/
- Integration manifest:
  https://developers.home-assistant.io/docs/creating_integration_manifest/
- Diagnostics:
  https://developers.home-assistant.io/docs/core/integration/diagnostics/

Core guidance to apply:

- New integrations should target at least Bronze quality scale.
- Product/service communication should live in a separate Python library.
- The initial PR should be as small as possible.
- The PR description must link the communication library repository.
- Config entry runtime state should use `ConfigEntry.runtime_data`.
- Config flow, unload, service actions, diagnostics, and docs need real Home
  Assistant tests and documentation.

## Current Core Blockers

### 1. Aruba protocol implementation is inside the integration

Current state:

- `custom_components/aruba_ble_proxy/aruba_proto.py` loads generated protobuf
  modules from `custom_components/aruba_ble_proxy/proto_generated`.
- Aruba protocol models, WebSocket receiver, action encoding, active GATT
  handling, and CLI rendering are all inside the integration package.

Core target:

- Extract Aruba protocol and transport code to a separate PyPI package.
- The Home Assistant integration should import that package through
  `manifest.json` requirements.
- The Home Assistant integration should contain HA lifecycle, config flow,
  Bluetooth scanner registration, diagnostics, and service action glue only.

Suggested package name:

- `aruba-iot-ble`

Suggested import package:

- `aruba_iot_ble`

### 2. Manifest is not core-ready

Current state:

- `codeowners` is empty.
- `requirements` only lists generic dependencies.
- No quality scale metadata.
- No external issue tracker for core docs flow.
- No `loggers` field for library logger names.

Core target:

- Add a real codeowner.
- Replace direct protocol dependencies with the extracted library requirement.
- Add `loggers` for the extracted library.
- Add quality scale metadata according to current HA requirements.
- Move user-facing docs to the Home Assistant documentation format when opening
  a core PR.

### 3. Runtime state uses `hass.data`

Current state:

- The runtime is stored in `hass.data[DOMAIN][entry.entry_id]`.
- Helper lookup code iterates `hass.data` to find the active runtime.

Core target:

- Define a typed config entry alias, for example:
  `type ArubaBleProxyConfigEntry = ConfigEntry[ArubaBleProxyRuntime]`.
- Store the runtime in `entry.runtime_data`.
- Use typed config entries through setup, unload, services, diagnostics, and
  options flow.

### 4. Config flow does not perform enough validation

Current state:

- The flow creates the entry after collecting listener and CLI data.
- It does not meaningfully test whether the listener can bind or whether the
  setup is usable.

Core target:

- Validate port range with HA selectors and schema.
- Attempt a listener bind check before entry creation, or provide a documented
  reason why a full Aruba connectivity test is impossible at config time.
- Prevent duplicate listener entries.
- Keep AP source entries unique.
- Add config flow tests using Home Assistant test fixtures.

### 5. Tests are useful but not core-style tests

Current state:

- Tests use local stubs and direct module tests.
- This is good for HACS velocity but not enough for HA core review.

Core target:

- Add tests under Home Assistant core style:
  `tests/components/aruba_ble_proxy/`.
- Use HA fixtures such as `hass`, `MockConfigEntry`, service calls, config flow
  helpers, and unload/reload flows.
- Keep lower-level protocol tests in the extracted library.
- Reach the quality scale coverage target for integration modules.

## Target Architecture

### Package split

#### Python library: `aruba_iot_ble`

Owns product/protocol communication:

- Aruba protobuf generated modules.
- Telemetry decoder.
- BLE advertisement model conversion independent from HA.
- Aruba WebSocket receiver transport primitives.
- Aruba action encoder/decoder.
- Active BLE/GATT session model.
- GATT service discovery representation.
- Compatibility override registry and generic override engine.
- Aruba CLI rendering helpers.

Must not import Home Assistant.

Expected public API shape:

```python
from aruba_iot_ble import (
    ArubaTelemetryDecoder,
    ArubaTelemetryMessage,
    ArubaBleEvent,
    ArubaBleReceiver,
    ArubaActionRequest,
    ArubaActionResult,
    ArubaGattService,
    ArubaGattCharacteristic,
    CompatibilityOverrideRegistry,
    apply_gatt_overrides,
    render_aruba_config,
    render_aruba_cleanup_config,
)
```

#### Home Assistant integration: `aruba_ble_proxy`

Owns Home Assistant behavior:

- Config flow and options flow.
- Config entry lifecycle.
- `entry.runtime_data`.
- WebSocket listener lifecycle using the library.
- Bluetooth scanner/source registration.
- Conversion to `BluetoothServiceInfoBleak`.
- Service actions for active BLE/GATT.
- Diagnostics and token redaction.
- Translations, `services.yaml`, manifest, docs.

## Compatibility Override Architecture

The current SwitchBot fallback is functional, but it is too close to the
generic GATT client code. The next architecture should keep the generic code
clean and move vendor-specific facts into structured override data.

### Design goal

The generic GATT path should only say:

1. Aruba reported these advertised services.
2. Aruba reported these GATT services/characteristics.
3. Load declared compatibility overrides.
4. Apply only overrides whose match rules are satisfied.
5. Never replace real Aruba-discovered characteristics.
6. Expose which overrides were applied in diagnostics.

The generic GATT code must not contain SwitchBot-specific UUID constants.

### Override location

Prefer placing overrides in the extracted library:

```text
aruba_iot_ble/
  compatibility/
    schema.py
    registry.py
    overrides/
      switchbot_fd3d.yaml
```

If the library is not extracted yet, use the same structure temporarily inside
the custom integration:

```text
custom_components/aruba_ble_proxy/data/compatibility_overrides/
  switchbot_fd3d.yaml
```

Do not load arbitrary code from these files. They are static data shipped with
the package and validated by schema.

### Override schema

Example:

```yaml
id: switchbot_fd3d_command_service
vendor: switchbot
status: compatibility
reason: Aruba firmware may report the FD3D advertisement service without the
  command service characteristics required by PySwitchbot.
match:
  advertised_service_uuids:
    - "0000fd3d-0000-1000-8000-00805f9b34fb"
  require_missing_any_characteristic_uuids:
    - "cba20002-224d-11e6-9fb8-0002a5d5c51b"
    - "cba20003-224d-11e6-9fb8-0002a5d5c51b"
add_services:
  - service_uuid: "cba20d00-224d-11e6-9fb8-0002a5d5c51b"
    characteristics:
      - characteristic_uuid: "cba20002-224d-11e6-9fb8-0002a5d5c51b"
        properties:
          - write-without-response
        max_write_without_response_size: 20
      - characteristic_uuid: "cba20003-224d-11e6-9fb8-0002a5d5c51b"
        properties:
          - notify
          - read
```

### Override guardrails

- Overrides are data, not executable code.
- Each override needs a stable `id`.
- Each override needs a documented reason.
- Each override needs strict match conditions.
- Overrides may add missing services/characteristics only.
- Overrides must not mutate payload bytes.
- Overrides must not decode vendor application protocols.
- Overrides must not replace Aruba-provided characteristics.
- Overrides must be logged at debug level and exposed in diagnostics.
- Each override must have tests for:
  - match succeeds when expected;
  - match does not apply to unrelated devices;
  - existing Aruba characteristics are preserved;
  - partial missing characteristic cases;
  - resulting Bleak service collection compatibility.

### Runtime diagnostics for overrides

Expose counters like:

```json
{
  "compatibility_overrides_loaded": 1,
  "compatibility_overrides_applied": {
    "switchbot_fd3d_command_service": 2
  },
  "last_compatibility_override_applications": [
    {
      "id": "switchbot_fd3d_command_service",
      "source": "F4:2E:7F:C6:65:28",
      "device": "B0:E9:FE:A4:56:20"
    }
  ]
}
```

Redact or truncate device identifiers if required by HA diagnostics review.

## GATT Core Strategy

GATT remains part of the candidate. The risk is not technical only; it is review
scope. Home Assistant docs recommend keeping the first PR small and avoiding
non-essential custom service actions. This plan accepts that risk but requires
the GATT implementation to be presented cleanly.

Required GATT hardening before core submission:

- All active BLE/GATT actions raise HA service exceptions on failure.
- Service schemas validate MAC addresses, UUIDs, timeouts, and hex payloads.
- Active connection slots are bounded and documented.
- GATT state is scoped by AP source and BLE device.
- Disconnect, source loss, timeout, and concurrent operations have tests.
- Notification callback lifecycle is covered by tests.
- Services are documented in HA docs.
- The integration clearly states unsupported GATT features:
  - pairing;
  - bonding;
  - unpairing;
  - descriptor read/write;
  - generic invention of missing GATT surfaces.

If HA reviewers reject GATT in the first PR, do not remove it from the project.
Instead:

- Keep GATT in HACS/mainline.
- Split a passive-only core PR only after explicit maintainer decision.
- Re-submit GATT as a follow-up PR.

## Work Packages

### WP0 - Freeze baseline

Goal:

- Preserve current 1.0 behavior before invasive refactoring.

Tasks:

- Tag and keep current release state.
- Add a short architecture note describing current behavior.
- Keep a full test run result recorded.

Acceptance:

- Current HACS integration remains installable.
- Existing tests pass before extraction starts.

### WP1 - Extract `aruba_iot_ble` library

Goal:

- Move Aruba protocol/product communication out of the integration.

Tasks:

- Create a separate package repository or subdirectory prepared for extraction.
- Move protobuf generated files into the library.
- Move decoder models and protobuf loading into the library.
- Move Aruba action models and encoding into the library.
- Move WebSocket receiver primitives into the library if they remain HA-neutral.
- Move CLI rendering helpers into the library.
- Move compatibility override registry into the library.
- Add `py.typed`.
- Add library tests.
- Publish or prepare a PyPI release.

Acceptance:

- Home Assistant integration imports protocol code from `aruba_iot_ble`.
- `custom_components/aruba_ble_proxy/proto_generated` no longer exists.
- Library tests cover decoder, actions, CLI rendering, and overrides.
- Integration tests still pass.

### WP2 - Refactor HA runtime to `entry.runtime_data`

Goal:

- Align runtime lifecycle with HA quality scale.

Tasks:

- Define a typed config entry alias.
- Store runtime in `entry.runtime_data`.
- Update setup, unload, services, diagnostics, and options flow.
- Remove runtime lookup by scanning `hass.data`.
- Keep a small domain-level registry only if service actions truly need global
  lookup by AP source.

Acceptance:

- No runtime object is stored as primary state in `hass.data`.
- Unload stops the runtime and leaves no active receiver task.
- Reload works from options flow.

### WP3 - Manifest and metadata

Goal:

- Make manifest acceptable for core review.

Tasks:

- Add real `codeowners`.
- Replace direct protocol dependencies with `aruba-iot-ble==x.y.z`.
- Add `loggers` for `aruba_iot_ble`.
- Add current quality scale metadata required by HA.
- Verify `iot_class` remains `local_push`.
- Decide whether `bluetooth: []` is correct or whether this integration should
  avoid Bluetooth discovery matchers because it provides scanner sources rather
  than discovering Aruba APs over BLE.

Acceptance:

- Manifest passes HA validation.
- Metadata matches current HA docs.

### WP4 - Config flow and options flow

Goal:

- Make setup robust and testable.

Tasks:

- Validate bind port before creating the listener entry.
- Abort duplicate listener entries.
- Preserve AP source unique IDs.
- Validate endpoint path format.
- Validate public host enough to avoid unusable CLI output.
- Regenerate token only when empty.
- Add tests for user flow, duplicate flow, options flow, AP source discovery,
  reload after options, and invalid input.

Acceptance:

- Config flow has full HA-style test coverage.
- User-facing errors are translated.

### WP5 - Passive BLE scanner path

Goal:

- Keep passive BLE forwarding as the stable core path.

Tasks:

- Keep Aruba APs registered as Bluetooth scanner sources.
- Keep advertisement conversion isolated and tested.
- Ensure source AP is represented consistently.
- Confirm scanner unload removes sources/callbacks.
- Confirm malformed Aruba frames are dropped without breaking the receiver.

Acceptance:

- BTHome and other HA Bluetooth consumers receive standard
  `BluetoothServiceInfoBleak`.
- No application payload decoding is added.

### WP6 - Active BLE/GATT path

Goal:

- Keep GATT in the candidate while making it reviewable.

Tasks:

- Keep active client implementation generic.
- Move vendor facts to compatibility overrides.
- Add strict service schemas.
- Convert failures to HA service exceptions.
- Add tests for:
  - connect success/failure;
  - disconnect success/failure;
  - read/write/notify;
  - source-scoped GATT state;
  - AP source disconnect while operation is in flight;
  - send timeout;
  - connection slot behavior;
  - compatibility override application.

Acceptance:

- GATT tests do not rely on a real SwitchBot device.
- Vendor compatibility tests exercise the override engine, not generic client
  special cases.

### WP7 - Diagnostics

Goal:

- Provide supportable diagnostics without adding recorder entities.

Tasks:

- Add `diagnostics.py`.
- Return config entry data with token redacted.
- Include receiver stats.
- Include connected AP sources.
- Include active slot state.
- Include recent action result summaries.
- Include compatibility override counters.
- Exclude raw BLE payloads by default unless clearly safe.

Acceptance:

- Diagnostics can be downloaded from the config entry.
- Sensitive data is redacted.
- Tests verify redaction.

### WP8 - Security and robustness

Goal:

- Reduce obvious core review objections around the listener.

Tasks:

- Keep generated token default.
- Require token validation for every binary telemetry message.
- Add bounded message size if supported by the WebSocket server.
- Add invalid-token rate limiting or connection close/backoff accounting.
- Keep send timeout.
- Ensure decode errors do not kill the receiver.
- Ensure receiver task crashes are surfaced and tested.
- Document that network exposure depends on user firewall/reverse proxy setup.

Acceptance:

- Invalid tokens cannot cause unbounded memory or task growth.
- Receiver failures are visible in diagnostics.

### WP9 - Service actions

Goal:

- Make service actions acceptable if kept in core PR.

Tasks:

- Ensure all service actions are registered in `async_setup`.
- Ensure service action docs exist.
- Ensure service actions raise proper exceptions on failures.
- Ensure `services.yaml` has descriptions, selectors, examples where current HA
  docs expect them.
- Add HA service call tests.

Acceptance:

- Each service has a test for success and failure.
- User-facing service descriptions are complete.

### WP10 - Documentation and brands

Goal:

- Prepare for Home Assistant docs/brands review.

Tasks:

- Write Home Assistant integration docs in the official docs format.
- Document installation parameters.
- Document configuration options.
- Document data update behavior.
- Document removal instructions.
- Document GATT limits.
- Document service actions.
- Add troubleshooting section.
- Prepare brand assets for the HA brands repository if required.

Acceptance:

- Docs explain what the integration does and does not do without marketing.
- Docs do not imply universal BLE support.

## Suggested PR Strategy

### Preferred strategy for this project

Submit one core candidate with:

- extracted library;
- passive BLE scanner support;
- active BLE/GATT support;
- structured compatibility overrides;
- diagnostics;
- HA-style tests.

This respects the product decision that GATT is part of the integration.

### Risk

Home Assistant reviewers may still ask to split active GATT and custom service
actions out of the first PR because official guidance prefers small initial
PRs.

### Response if challenged

Do not remove GATT from the project. Instead respond with:

- GATT is already field-tested and is part of the user value.
- The implementation is source-scoped, bounded, tested, and documented.
- Vendor-specific compatibility is isolated in declarative override data.
- If maintainers require a smaller first PR, create a passive-only core branch
  as a review strategy, while HACS/mainline keeps GATT.

## Definition of Done for Core Candidate

- Protocol code extracted to `aruba_iot_ble`.
- No generated protobuf files remain inside the HA integration.
- Manifest has codeowners and current required metadata.
- Runtime uses `entry.runtime_data`.
- Config flow validates setup enough for Bronze.
- Unload/reload is tested.
- Diagnostics are implemented and redact secrets.
- GATT services are documented and tested.
- Compatibility overrides are declarative and isolated.
- No SwitchBot UUID constants remain in the generic GATT client.
- HA-style tests exist for config flow, runtime lifecycle, services,
  diagnostics, passive scanner, active GATT, and override behavior.
- Existing HACS behavior remains intact or any breaking change is explicitly
  documented.

## First Tasks for the Next Implementer

1. Create an `aruba_iot_ble` package skeleton.
2. Move protobuf generated files and `aruba_proto.py` logic into the package.
3. Replace integration imports with library imports.
4. Add compatibility override registry and move SwitchBot fallback data out of
   `active_client.py`.
5. Refactor runtime storage to `entry.runtime_data`.
6. Add `diagnostics.py`.
7. Convert tests into a split structure:
   - library unit tests for protocol/override code;
   - HA integration tests for config/runtime/services/diagnostics.
8. Update manifest and docs only after the library boundary is stable.

