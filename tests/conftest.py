import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def pytest_collection_modifyitems(config, items):
    if os.environ.get("CI"):
        skip_e2e = pytest.mark.skip(reason="e2e tests need audio/display/model download; run locally")
        for item in items:
            if "e2e" in item.keywords:
                item.add_marker(skip_e2e)
