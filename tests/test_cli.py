from custom_components.aruba_ble_proxy.cli import parse_args


def test_cli_reads_environment(monkeypatch):
    monkeypatch.setenv("ARUBA_BLE_PROXY_HOST", "127.0.0.1")
    monkeypatch.setenv("ARUBA_BLE_PROXY_PORT", "17443")
    monkeypatch.setenv("ARUBA_BLE_PROXY_ACCESS_TOKEN", "secret")
    monkeypatch.setenv("ARUBA_BLE_PROXY_LOG_LEVEL", "debug")

    args = parse_args([])

    assert args.host == "127.0.0.1"
    assert args.port == 17443
    assert args.access_token == "secret"
    assert args.log_level == "debug"


def test_cli_flags_override_environment(monkeypatch):
    monkeypatch.setenv("ARUBA_BLE_PROXY_HOST", "127.0.0.1")
    monkeypatch.setenv("ARUBA_BLE_PROXY_PORT", "17443")

    args = parse_args(["--host", "0.0.0.0", "--port", "7443"])

    assert args.host == "0.0.0.0"
    assert args.port == 7443


def test_cli_reads_summary_environment(monkeypatch):
    monkeypatch.setenv("ARUBA_BLE_PROXY_SUMMARY", "true")

    args = parse_args([])

    assert args.summary is True
