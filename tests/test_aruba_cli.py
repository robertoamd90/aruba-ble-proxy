from pathlib import Path

import pytest

from custom_components.aruba_ble_proxy.aruba_cli import (
    default_uuid_seed_path,
    normalize_uuid16,
    parse_uuid_file,
    render_aruba_config,
    render_aruba_cleanup_config,
    render_radio_profile,
    render_transport_profiles,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("FCD2", "FCD2"),
        ("0xfe95", "FE95"),
        ("0000fd3d-0000-1000-8000-00805f9b34fb", "FD3D"),
    ],
)
def test_normalize_uuid16(value, expected):
    assert normalize_uuid16(value) == expected


def test_normalize_uuid16_rejects_non_uuid16():
    with pytest.raises(ValueError, match="only 16-bit"):
        normalize_uuid16("12345678-1234-1234-1234-123456789abc")


def test_parse_uuid_file_deduplicates_and_ignores_comments(tmp_path: Path):
    uuid_file = tmp_path / "uuids.txt"
    uuid_file.write_text(
        """
        # comment
        FCD2
        0xfe95 # inline comment
        0000fcd2-0000-1000-8000-00805f9b34fb
        """,
        encoding="utf-8",
    )

    assert parse_uuid_file(uuid_file) == ["FCD2", "FE95"]


def test_default_uuid_seed_path_exists():
    assert default_uuid_seed_path().exists()
    assert "FCD2" in parse_uuid_file(default_uuid_seed_path())


def test_render_transport_profiles_chunks_filters():
    cli = render_transport_profiles(
        uuids=["FCD2", "FE95", "FD3D"],
        name_prefix="ha-ble",
        endpoint_url="ws://192.0.2.10:7443/test",
        token="example-access-token",
        chunk_size=2,
    )

    assert "iot transportProfile ha-ble-01" in cli
    assert "serviceUUIDFilter FCD2,FE95" in cli
    assert "iot transportProfile ha-ble-02" in cli
    assert "serviceUUIDFilter FD3D" in cli
    assert cli.endswith("commit apply\n")


def test_render_radio_profile():
    lines = render_radio_profile(radio_profile="ha-ble-radio")

    assert lines == [
        "iot radio-profile ha-ble-radio",
        "radio-instance internal",
        "radio-mode ble",
        "ble-opmode scanning",
        "ble-console off",
        "ble-txpower 0",
        "exit",
        "iot use-radio-profile ha-ble-radio",
    ]


def test_render_aruba_config_includes_radio_profile_by_default():
    cli = render_aruba_config(
        uuids=["FCD2"],
        name_prefix="ha-ble",
        endpoint_url="ws://192.0.2.10:7443/test",
        token="example-access-token",
    )

    assert "iot radio-profile ha-ble-radio" in cli
    assert "iot use-radio-profile ha-ble-radio" in cli
    assert "iot transportProfile ha-ble-01" in cli


def test_render_aruba_cleanup_config_removes_use_before_profiles():
    cli = render_aruba_cleanup_config(
        name_prefix="ha-ble",
        profile_count=2,
        radio_profile="ha-ble-radio",
    )

    assert cli.splitlines() == [
        "configure terminal",
        "no iot useTransportProfile ha-ble-01",
        "no iot useTransportProfile ha-ble-02",
        "no iot use-radio-profile ha-ble-radio",
        "no iot transportProfile ha-ble-01",
        "no iot transportProfile ha-ble-02",
        "no iot radio-profile ha-ble-radio",
        "end",
        "commit apply",
    ]
