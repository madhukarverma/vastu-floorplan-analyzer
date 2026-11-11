from pathlib import Path

import pytest

from vastu_analyzer import load_plan
from vastu_analyzer.models import FloorPlan

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


@pytest.fixture
def sample_path() -> Path:
    return EXAMPLES / "sample_3bhk_delhi.json"


@pytest.fixture
def compliant_path() -> Path:
    return EXAMPLES / "compliant_3bhk.json"


@pytest.fixture
def sample_plan(sample_path: Path) -> FloorPlan:
    return load_plan(sample_path)


@pytest.fixture
def compliant_plan(compliant_path: Path) -> FloorPlan:
    return load_plan(compliant_path)
