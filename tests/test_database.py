import pytest

from repopilot.api import create_app
from repopilot.database import validate_database
from repopilot.owner import OwnerConfig
from repopilot.store import Store


@pytest.mark.parametrize(
    "schema",
    ["public", "auth", "storage", "extensions", "information_schema", "pg_catalog", "a;b", "a.b"],
)
def test_shared_or_injected_schema_rejected_before_connection(schema):
    with pytest.raises(ValueError, match="private_database_schema_required"):
        Store("postgresql+psycopg://unused.invalid/db", schema=schema)


def test_sqlite_is_local_only_and_cannot_ignore_schema(tmp_path):
    url = f"sqlite:///{tmp_path / 'state.db'}"
    with pytest.raises(ValueError, match="production_requires_private_postgres"):
        Store(url, production=True)
    with pytest.raises(ValueError, match="private_database_schema_required"):
        Store(url, schema="repopilot_private")
    assert not (tmp_path / "state.db").exists()


@pytest.mark.parametrize(
    "host",
    ["db.example.supabase.co", "aws-0-region.pooler.supabase.com", "DB.EXAMPLE.SUPABASE.CO."],
)
def test_supabase_requires_private_schema_and_verified_tls(host):
    url = f"postgresql+psycopg://user@{host}/postgres"
    with pytest.raises(ValueError, match="production_requires_private_postgres"):
        validate_database(url, None)
    for mode in ["disable", "prefer", "require", "verify-ca"]:
        with pytest.raises(ValueError, match="database_certificate_verification_required"):
            validate_database(url + "?sslmode=" + mode, "repopilot_private")
    validate_database(url + "?sslmode=verify-full", "repopilot_private", production=True)


def test_invalid_owner_config_has_no_database_side_effects(tmp_path):
    root = tmp_path / "uncreated"
    with pytest.raises(ValueError, match="owner_password_hash_required"):
        create_app(workspace=root, owner_config=OwnerConfig(mode="owner"))
    assert not root.exists()


def test_production_cannot_silently_fall_back_to_sqlite(tmp_path, monkeypatch):
    from repopilot.owner_auth import password_hash

    monkeypatch.setenv("REPOPILOT_ENV", "production")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    cfg = OwnerConfig(
        mode="owner", origin="https://owner.example", password=password_hash("test-password-only")
    )
    with pytest.raises(ValueError, match="production_requires_private_postgres"):
        create_app(workspace=tmp_path, owner_config=cfg)
    assert not (tmp_path / "runs.db").exists()
