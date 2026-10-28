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
