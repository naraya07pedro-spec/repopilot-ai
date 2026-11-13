def test_list_uses_one_query_and_keeps_public_recent_limit(store, monkeypatch):
    public_ids = []
    for i in range(115):
        data, fresh = store.create(f"recent-public-{i}", {"scenario": "bug"}, True)
        assert fresh
        public_ids.append(data["id"])
    private, fresh = store.create("recent-operator", {"scenario": "feature"}, False)
    assert fresh

    # The public listing must not fetch each row again through Store.get().
    def no_point_queries(_identity):
        raise AssertionError("list must not execute per-record get queries")

    monkeypatch.setattr(store, "get", no_point_queries)
    listed = store.list(public_only=True)
    assert len(listed) == 100
    assert all(item["public"] and item["id"] != private["id"] for item in listed)
    assert [item["id"] for item in listed] == list(reversed(public_ids[-100:]))
    assert len(store.list()) == 100
