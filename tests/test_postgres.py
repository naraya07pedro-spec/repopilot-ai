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
