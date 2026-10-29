import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

from repopilot.store import Store


@pytest.mark.skipif(not os.environ.get("TEST_POSTGRES_URL"), reason="PostgreSQL not configured")
def test_postgres_unique_reservation_and_claim():
    store = Store(os.environ["TEST_POSTGRES_URL"])
    key = uuid.uuid4().hex
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: store.create(key, {"scenario": "bug"}, False), range(8)))
    assert sum(fresh for _, fresh in results) == 1
    identity = results[0][0]["id"]
    with ThreadPoolExecutor(max_workers=8) as pool:
        claims = list(pool.map(lambda _: store.claim(identity, "queued", "planning"), range(8)))
    assert sum(claims) == 1
    store.engine.dispose()


@pytest.mark.skipif(not os.environ.get("TEST_POSTGRES_URL"), reason="PostgreSQL not configured")
def test_postgres_owner_migration_persistence_and_recovery():
    from test_owner import Source, planner

    from repopilot.migrations import migrate
    from repopilot.owner_auth import OwnerAuth, password_hash
    from repopilot.private_service import PrivateService

    store = Store(os.environ["TEST_POSTGRES_URL"])
    migrate(store.engine)
    migrate(store.engine)
    password = "Postgres persistence fixture password"
    auth = OwnerAuth(store.engine, password_hash(password))
    token = auth.login(password)
    service = PrivateService(store.engine, Source(), planner(store))
    key = uuid.uuid4().hex
    with ThreadPoolExecutor(max_workers=4) as pool:
        rows = list(pool.map(lambda _: service.create(Source.allowed[0], 1, key), range(4)))
    assert sum(fresh for _, fresh in rows) == 1
    identity = rows[0][0]["id"]
    store.engine.dispose()
    reopened = Store(os.environ["TEST_POSTGRES_URL"])
    recovered = PrivateService(reopened.engine, None, None)
    assert OwnerAuth(reopened.engine, "").valid(token)
    recovered.recover()
    assert recovered.get(identity)["status"] == "interrupted"
    assert recovered.get(identity)["repository"] == Source.allowed[0]
    OwnerAuth(reopened.engine, "").logout(token)
    assert not OwnerAuth(reopened.engine, "").valid(token)
    reopened.engine.dispose()


@pytest.mark.skipif(not os.environ.get("TEST_POSTGRES_URL"), reason="PostgreSQL not configured")
def test_private_schema_isolation_and_recovery():
    from sqlalchemy import create_engine, inspect, select, text
    from sqlalchemy.engine import make_url
    from sqlalchemy.schema import CreateSchema, DropSchema
    from test_owner import Source, planner

    from repopilot.migrations import migrate, sessions
    from repopilot.owner_auth import OwnerAuth, password_hash
    from repopilot.private_service import PrivateService

    url = os.environ["TEST_POSTGRES_URL"]
    admin = create_engine(url)
    schema = "repopilot_test_" + uuid.uuid4().hex
    role = "repopilot_role_" + uuid.uuid4().hex
    probe = "repopilot_probe_" + uuid.uuid4().hex
    before = set(inspect(admin).get_table_names(schema="public"))
    with admin.begin() as connection:
        connection.exec_driver_sql(f"CREATE ROLE {role} NOLOGIN NOSUPERUSER NOBYPASSRLS")
        connection.exec_driver_sql(f"CREATE ROLE {probe} NOLOGIN NOSUPERUSER NOBYPASSRLS")
        connection.execute(CreateSchema(schema))
        connection.exec_driver_sql(f"ALTER SCHEMA {schema} OWNER TO {role}")
        connection.exec_driver_sql(f"GRANT USAGE ON SCHEMA {schema} TO PUBLIC")
    scoped_url = make_url(url).update_query_dict({"options": "-c role=" + role})
    scoped_url_text = scoped_url.render_as_string(hide_password=False)
    try:
        store = Store(scoped_url_text, schema=schema)
        migrate(store.engine)
        auth = OwnerAuth(store.engine, password_hash("schema-test-password"))
        token = auth.login("schema-test-password")
        service = PrivateService(store.engine, Source(), planner(store))
        run, _ = service.create(Source.allowed[0], 1, uuid.uuid4().hex)
        store.engine.dispose()
        reopened = Store(scoped_url_text, schema=schema)
        migrate(reopened.engine)
        recovered = PrivateService(reopened.engine, None, None)
        recovered.recover()
        assert recovered.get(run["id"])["status"] == "interrupted"
        assert OwnerAuth(reopened.engine, "").valid(token)
        with reopened.engine.connect() as connection:
            assert connection.scalar(text("SELECT current_user")) == role
            assert len(connection.execute(select(sessions)).all()) == 1
        assert set(inspect(admin).get_table_names(schema=schema)) == {
            "runs",
            "schema_versions",
            "owner_sessions",
            "engineering_runs",
            "model_budgets",
        }
        assert set(inspect(admin).get_table_names(schema="public")) == before
        with admin.connect() as connection:
            policies = (
                connection.execute(
                    text(
                        "SELECT relrowsecurity FROM pg_class c JOIN pg_namespace n "
                        "ON n.oid=c.relnamespace WHERE n.nspname=:schema AND c.relkind='r'"
                    ),
                    {"schema": schema},
                )
                .scalars()
                .all()
            )
            assert len(policies) == 5 and all(policies)
            assert not connection.scalar(
                text("SELECT has_schema_privilege(:role, :schema, 'USAGE')"),
                {"role": probe, "schema": schema},
            )
        reopened.engine.dispose()
        with pytest.raises(ValueError, match="private_database_schema_missing"):
            Store(url, schema="missing_" + uuid.uuid4().hex)
    finally:
        # Only the unique schema created by this test in the explicit test database.
        with admin.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
            connection.exec_driver_sql(f"DROP ROLE {role}")
            connection.exec_driver_sql(f"DROP ROLE {probe}")
        admin.dispose()


@pytest.mark.skipif(not os.environ.get("TEST_POSTGRES_URL"), reason="PostgreSQL not configured")
def test_bootstrap_with_non_superuser_administrator():
    from pathlib import Path

    from sqlalchemy import create_engine, inspect, text
    from sqlalchemy.schema import DropSchema

    engine = create_engine(os.environ["TEST_POSTGRES_URL"])
    suffix = uuid.uuid4().hex
    admin_role, role, schema = "rp_admin_" + suffix, "rp_role_" + suffix, "rp_schema_" + suffix
    with engine.begin() as connection:
        database = engine.dialect.identifier_preparer.quote(
            connection.scalar(text("SELECT current_database()"))
        )
        connection.exec_driver_sql(f"CREATE ROLE {admin_role} NOLOGIN NOSUPERUSER CREATEROLE")
        connection.exec_driver_sql(f"GRANT CREATE ON DATABASE {database} TO {admin_role}")
    script = Path("deploy/private-schema.sql").read_text()
    script = script.replace("repopilot_service", role).replace("repopilot_private", schema)
    script = script.replace("BEGIN;", "").replace("COMMIT;", "")
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql(f"SET LOCAL ROLE {admin_role}")
            connection.exec_driver_sql(script)
            connection.exec_driver_sql(f"SET LOCAL ROLE {role}")
            connection.exec_driver_sql(f"CREATE TABLE {schema}.probe (id integer)")
            assert connection.scalar(text("SELECT current_user")) == role
        assert inspect(engine).has_table("probe", schema=schema)
        with engine.connect() as connection:
            assert not connection.scalar(
                text(
                    "SELECT rolcanlogin OR rolsuper OR rolcreatedb OR rolcreaterole OR "
                    "rolreplication OR rolbypassrls OR rolinherit FROM pg_roles WHERE rolname=:role"
                ),
                {"role": role},
            )
    finally:
        # Unique objects in the explicit throwaway test database only.
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True, if_exists=True))
            connection.exec_driver_sql(f"DROP ROLE IF EXISTS {role}")
            connection.exec_driver_sql(f"REVOKE CREATE ON DATABASE {database} FROM {admin_role}")
            connection.exec_driver_sql(f"DROP ROLE {admin_role}")
        engine.dispose()
