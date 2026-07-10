from adhdolib.config import load_config, home

def test_defaults_without_file(adhdo_home):
    cfg = load_config()
    assert cfg["nudge"]["max_per_hour"] == 4
    assert cfg["nudge"]["quiet_hours"] == ["22:00", "07:00"]
    assert cfg["disk_warn_pct"] == 94

def test_file_overrides_merge(adhdo_home):
    (adhdo_home / "config.yaml").write_text("nudge:\n  max_per_hour: 2\n")
    cfg = load_config()
    assert cfg["nudge"]["max_per_hour"] == 2
    assert cfg["nudge"]["quiet_hours"] == ["22:00", "07:00"]  # default kept

def test_home_respects_env(adhdo_home):
    assert home() == adhdo_home
