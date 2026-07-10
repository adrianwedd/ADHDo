from adhdolib.binload import load_bin_module


def test_load_bin_module_wake():
    mod = load_bin_module("wake")
    assert hasattr(mod, "inject")
