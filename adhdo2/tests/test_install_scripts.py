import configparser, pathlib, re

ROOT = pathlib.Path(__file__).resolve().parents[1]


def test_install_cron_has_no_slash25_heartbeat():
    text = (ROOT / "scripts" / "install-cron.sh").read_text()
    assert "*/25" not in text, "cron */25 gives a 10-min gap at hour boundaries"
    # heartbeat must be installed via the systemd timer instead
    assert "adhdo-heartbeat.timer" in text
    assert "systemctl --user enable --now adhdo-heartbeat.timer" in text


def test_install_cron_keeps_other_entries():
    text = (ROOT / "scripts" / "install-cron.sh").read_text()
    for needle in ["--event meds", "--event bedtime", "adhdo-dispatch",
                   "adhdo-watchdog.sh", "adhdo-recycle.sh",
                   "@reboot", "adhdo-catchup.sh"]:
        assert needle in text


def test_heartbeat_timer_true_25min_cadence():
    cp = configparser.ConfigParser()
    cp.read(ROOT / "systemd" / "adhdo-heartbeat.timer")
    assert cp["Timer"]["OnUnitActiveSec"] == "25min"
    assert "OnBootSec" in cp["Timer"]
    assert cp["Install"]["WantedBy"] == "timers.target"


def test_heartbeat_service_runs_wake_heartbeat():
    cp = configparser.ConfigParser(interpolation=None)
    cp.read(ROOT / "systemd" / "adhdo-heartbeat.service")
    assert cp["Service"]["Type"] == "oneshot"
    assert "bin/wake" in cp["Service"]["ExecStart"]
    assert "[heartbeat]" in cp["Service"]["ExecStart"]


def test_deploy_installs_piper_and_timers():
    text = (ROOT / "scripts" / "deploy.sh").read_text()
    assert re.search(r"pip -q install .*piper-tts", text) or "install piper-tts" in text
    assert "systemd/*.timer" in text
