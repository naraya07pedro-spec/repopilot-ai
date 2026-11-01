"""Actionable CLI configuration errors; no model/runtime or listener starts."""

from types import SimpleNamespace

import pytest

from repopilot.local_cli import main


@pytest.mark.parametrize(
    ("arguments", "message"),
    [
        (["--port", "80"], "Choose a port"),
        (["--run-budget-micro", "-1"], "cannot be negative"),
        (["--profiles", "missing-profile-for-cli-test.json"], "Invalid model configuration"),
        (
            ["--model", "test", "--endpoint", "https://private:not-for-output@127.0.0.1"],
            "Invalid model configuration",
        ),
    ],
)
def test_invalid_configuration_is_reported_without_traceback(arguments, message, capsys):
    with pytest.raises(SystemExit) as error:
        main(["--repo", ".", *arguments])
    assert error.value.code == 2
    text = capsys.readouterr().err
    assert message in text
    assert "Traceback" not in text and "not-for-output" not in text


def test_empty_profile_catalog_is_actionable(tmp_path, capsys):
    path = tmp_path / "empty.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(SystemExit):
        main(["--repo", ".", "--profiles", str(path)])
    assert "at least one model" in capsys.readouterr().err


def test_launcher_binds_only_literal_loopback_and_prints_ascii(monkeypatch, capsys):
    import repopilot.local_cli as cli

    calls = []
    monkeypatch.setattr(
        cli,
        "create_local_app",
        lambda *a, **kw: SimpleNamespace(state=SimpleNamespace(session_token="test-session-only")),
    )
    monkeypatch.setattr(cli.uvicorn, "run", lambda *a, **kw: calls.append(kw))
    main(["--repo", ".", "--model", "already-installed"])
    assert calls == [{"host": "127.0.0.1", "port": 8765, "access_log": False}]
    text = capsys.readouterr().out
    text.encode("ascii")
    assert "never executed or applied" in text
