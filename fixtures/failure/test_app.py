import importlib.util
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
