import os, pathlib, sys, pytest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

@pytest.fixture
def adhdo_home(tmp_path, monkeypatch):
    monkeypatch.setenv("ADHDO_HOME", str(tmp_path))
    (tmp_path / "data").mkdir()
    return tmp_path
