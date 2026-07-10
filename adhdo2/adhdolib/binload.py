import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path


def load_bin_module(name: str):
    path = Path(__file__).resolve().parents[1] / "bin" / name
    loader = SourceFileLoader(f"{name}_cli", str(path))
    spec = importlib.util.spec_from_file_location(f"{name}_cli", path, loader=loader)
    mod = importlib.util.module_from_spec(spec)
    loader.exec_module(mod)
    return mod
