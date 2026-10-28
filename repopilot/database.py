"""Database configuration checks before connecting or creating application tables."""

import re

from sqlalchemy.engine import make_url


def validate_database(url: str, schema: str | None, production: bool = False) -> None:
    parsed = make_url(url)
    postgres = parsed.drivername == "postgresql+psycopg"
    if schema and (
        not postgres
        or not re.fullmatch(r"[a-z][a-z0-9_]{0,62}", schema)
        or schema in {"public", "information_schema", "auth", "storage", "extensions"}
        or schema.startswith("pg_")
    ):
        raise ValueError("private_database_schema_required")
    host = (parsed.host or "").lower().rstrip(".")
    supabase = host.endswith(".supabase.co") or host.endswith(".supabase.com")
    if production or supabase:
        if not postgres or not schema:
            raise ValueError("production_requires_private_postgres")
        if parsed.query.get("sslmode") != "verify-full":
            raise ValueError("database_certificate_verification_required")
