from pathlib import Path

import pytest

from cvmatch.config import Settings
from cvmatch.taxonomy import default_taxonomy

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def sample_cv() -> str:
    return (ROOT / "data" / "sample_cv.md").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def sample_offer() -> str:
    return (ROOT / "data" / "sample_offer.txt").read_text(encoding="utf-8")


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture(scope="session")
def taxonomy():
    return default_taxonomy()
