import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location("fixture_app", Path(__file__).with_name("app.py"))
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)


def test_normalize_tag():
    assert app.normalize_tag(" PYTHON ") == "python"
