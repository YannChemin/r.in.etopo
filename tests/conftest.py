"""Fixtures for the r.in.etopo tests.

The GRASS Python path comes from `grass --config python_path`, and
r.in.etopo.py is loaded with importlib, as its name is not a valid
module name. The functions tested here make no GRASS calls.
"""

import importlib.util
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

GRASS_BIN = shutil.which("grass")
if not GRASS_BIN:
    collect_ignore_glob = ["*"]
else:
    _python_path = subprocess.run(
        [GRASS_BIN, "--config", "python_path"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if _python_path not in sys.path:
        sys.path.insert(0, _python_path)


@pytest.fixture(scope="session")
def etopo():
    """The r.in.etopo.py module."""
    module_path = Path(__file__).resolve().parent.parent / "r.in.etopo.py"
    spec = importlib.util.spec_from_file_location("r.in.etopo", module_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod
