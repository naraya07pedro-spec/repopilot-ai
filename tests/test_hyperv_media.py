"""Integrity and no-overwrite checks; never boot/extract reference media."""

import hashlib
import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "media_preparer", Path(__file__).resolve().parents[1] / "scripts/prepare_hyperv_media.py"
)
media = importlib.util.module_from_spec(spec)
spec.loader.exec_module(media)


def test_media_verification_requires_exact_bytes(tmp_path, monkeypatch):
    payload = b"synthetic media fixture; no guest image"
    path = tmp_path / "sample.iso"
    path.write_bytes(payload)
    monkeypatch.setattr(media, "SIZE", len(payload))
    monkeypatch.setattr(media, "SHA256", hashlib.sha256(payload).hexdigest())
    verified = media.verify(path)
    assert not verified["worker_image_built"]
    assert not verified["boot_tested"]
    path.write_bytes(payload + b"!")
    with pytest.raises(ValueError, match="size_mismatch"):
        media.verify(path)
    path.write_bytes(b"x" * len(payload))
    with pytest.raises(ValueError, match="sha256_mismatch"):
        media.verify(path)


def test_existing_invalid_media_is_not_replaced(tmp_path, monkeypatch):
    path = tmp_path / media.NAME
    path.write_bytes(b"preserve existing bytes")
    monkeypatch.setattr(media, "checked_root", lambda: tmp_path)
    monkeypatch.setattr("sys.argv", ["prepare_hyperv_media.py", "--download"])
    with pytest.raises(ValueError, match="size_mismatch"):
        media.main()
    assert path.read_bytes() == b"preserve existing bytes"


def test_default_does_not_download_or_create_directory(tmp_path, monkeypatch, capsys):
    missing = tmp_path / "missing"
    monkeypatch.setattr(media, "checked_root", lambda: missing)
    monkeypatch.setattr("sys.argv", ["prepare_hyperv_media.py"])
    media.main()
    assert not missing.exists()
    assert '"downloaded": false' in capsys.readouterr().out


def test_redirect_cannot_change_origin():
    with pytest.raises(ValueError, match="origin_changed"):
        media.SameOrigin().redirect_request(None, None, 302, "", {}, "https://example.com/x")
