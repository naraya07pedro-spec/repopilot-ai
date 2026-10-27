import pytest

from repopilot.policy import PolicyError, digest, redact, repository_name, safe_path, validate_edits
from repopilot.runner import command_policy


@pytest.mark.parametrize(
    "name",
    [
        "../outside",
        "/etc/passwd",
        "C:/Windows/file",
        "a\\..\\x",
        ".git/config",
        ".env",
        "a/../../x",
        "app.py:secret",
        "NUL",
        "CON.txt",
        "a.",
        "a ",
        "",
        "foo;bar",
    ],
)
def test_paths_rejected(tmp_path, name):
    with pytest.raises(PolicyError):
        safe_path(tmp_path, name)


def test_safe_path(tmp_path):
    assert safe_path(tmp_path, "src/main.py") == tmp_path / "src/main.py"


def test_symlink(tmp_path):
    target = tmp_path / "target"
    target.write_text("secret")
    link = tmp_path / "alias.py"
    try:
        link.symlink_to(target)
    except OSError:
        pytest.skip("Host does not permit symlink creation")
    with pytest.raises(PolicyError):
        safe_path(tmp_path, "alias.py")


@pytest.mark.parametrize("repo", ["https://evil.org/x", "a/../b", "a/..", "a/b?x", "a\\b", "a/b/c"])
def test_ssrf_repository_rejected(repo):
    with pytest.raises(PolicyError):
        repository_name(repo)


def test_repository_and_digest():
    assert repository_name("owner/repo") == "owner/repo"
    assert digest({"b": 2, "a": 1}) == digest({"a": 1, "b": 2})


def test_redaction():
    token = "ghp_" + "a" * 30
    assert token not in redact("token=" + token)
    assert "[REDACTED]" in redact("Authorization: " + "Bearer " + "private")


@pytest.mark.parametrize(
    "edits,expected",
    [
        ({}, {}),
        ({"app.py": "import os; os.system('whoami')"}, {"app.py": "safe"}),
        ({"requirements.txt": "evil"}, {"app.py": "safe"}),
        ({"app.py": "ghp_" + "a" * 30}, {"app.py": "ghp_" + "a" * 30}),
    ],
)
def test_edit_policy(edits, expected):
    with pytest.raises(PolicyError):
        validate_edits(edits, expected)


def test_approved_edit_and_command():
    validate_edits({"app.py": "safe"}, {"app.py": "safe"})
    command_policy(["pytest"])
    with pytest.raises(PolicyError):
        command_policy(["sh", "-c", "curl example.com"])
