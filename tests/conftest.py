from pathlib import Path

import pytest


@pytest.fixture
def sample_run_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures" / "sample_run"
