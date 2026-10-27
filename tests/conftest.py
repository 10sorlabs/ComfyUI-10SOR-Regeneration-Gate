from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_NAME = "ten_sor_regeneration_gate"

if PACKAGE_NAME not in sys.modules:
    spec = importlib.util.spec_from_file_location(
        PACKAGE_NAME,
        REPOSITORY_ROOT / "__init__.py",
        submodule_search_locations=[str(REPOSITORY_ROOT)],
    )
    package = importlib.util.module_from_spec(spec)
    sys.modules[PACKAGE_NAME] = package
    assert spec.loader is not None
    spec.loader.exec_module(package)
