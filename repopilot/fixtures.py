"""Audited executable fixtures. Exact bytes are the host execution trust boundary."""

from dataclasses import dataclass

from repopilot.models import Issue

BUG = """def mean(values):
    if not values:
        raise ValueError("values must not be empty")
    return sum(values) // len(values)
"""
FIX = """def mean(values):
    if not values:
        raise ValueError("values must not be empty")
    return sum(values) / len(values)
"""
BUG_TESTS = """import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("fixture_app", Path(__file__).with_name("app.py"))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_fractional_mean():
    assert app.mean([1, 2]) == 1.5


def test_negative_mean():
    assert app.mean([-2, -1]) == -1.5


def test_empty_rejected():
    import pytest

    with pytest.raises(ValueError):
        app.mean([])
"""
FEATURE = """def normalize_tag(value):
    return value.strip().lower()
"""
FEATURE_TESTS = """import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("fixture_app", Path(__file__).with_name("app.py"))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_normalize_tag():
    assert app.normalize_tag(" PYTHON ") == "python"
"""
FEATURE_FIX = """def normalize_tag(value):
    return value.strip().lower()


def unique_tags(values):
    return list(dict.fromkeys(tag for value in values if (tag := normalize_tag(value))))
"""
FEATURE_NEW_TESTS = """import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("fixture_app", Path(__file__).with_name("app.py"))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_normalize_tag():
    assert app.normalize_tag(" PYTHON ") == "python"


def test_unique_tags_preserves_order():
    assert app.unique_tags([" AI ", "python", "ai", " "]) == ["ai", "python"]


def test_unique_tags_empty():
    assert app.unique_tags([]) == []
"""
BAD_FIX = """def mean(values):
    if not values:
        raise ValueError("values must not be empty")
    return round(sum(values) / len(values))
"""


@dataclass(frozen=True)
class Fixture:
    name: str
    title: str
    criteria: tuple[str, ...]
    files: dict[str, str]
    edits: dict[str, str]

    def issue(self) -> Issue:
        return Issue(
            number={"bug": 1, "feature": 2, "failure": 3}[self.name],
            title=self.title,
            body="\n".join(self.criteria),
        )


CATALOG = {
    "bug": Fixture(
        "bug",
        "Preserve fractional means",
        (
            "mean([1, 2]) returns 1.5",
            "Negative means preserve fractions",
            "Empty input raises ValueError",
        ),
        {"app.py": BUG, "test_app.py": BUG_TESTS},
        {"app.py": FIX},
    ),
    "feature": Fixture(
        "feature",
        "Add stable unique tag normalization",
        (
            "Normalize case and whitespace",
            "Skip empty tags",
            "Deduplicate while preserving input order",
        ),
        {"app.py": FEATURE, "test_app.py": FEATURE_TESTS},
        {"app.py": FEATURE_FIX, "test_app.py": FEATURE_NEW_TESTS},
    ),
    "failure": Fixture(
        "failure",
        "Detect a rounded-mean regression",
        ("Preserve fractional means", "Reject a rounded implementation when tests fail"),
        {"app.py": BUG, "test_app.py": BUG_TESTS},
        {"app.py": BAD_FIX},
    ),
}
