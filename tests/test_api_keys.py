from services.orchestrator.api_keys import ApiKeyStore


def test_create_returns_raw_once_and_stores_only_hash(tmp_path):
    store = ApiKeyStore(tmp_path / "api_keys.json")
    record, raw = store.create("member-a")
    assert raw.startswith("llmk_")
    assert record["label"] == "member-a"
    assert "hash" not in record  # public view never exposes the hash
    # Persisted file stores the hash, never the raw key.
    text = (tmp_path / "api_keys.json").read_text(encoding="utf-8")
    assert raw not in text
    assert "hash" in text


def test_verify_accepts_valid_and_rejects_unknown(tmp_path):
    store = ApiKeyStore(tmp_path / "api_keys.json")
    _, raw = store.create("member-a")
    assert store.verify(raw)["label"] == "member-a"
    assert store.verify("llmk_deadbeef_nope") is None


def test_revoke_disables_key_and_persists(tmp_path):
    path = tmp_path / "api_keys.json"
    store = ApiKeyStore(path)
    record, raw = store.create("member-a")
    assert store.verify(raw) is not None
    assert store.revoke(record["id"]) is True
    assert store.verify(raw) is None
    assert store.has_keys() is False
    # A fresh store loading the same file sees the revoked state.
    assert ApiKeyStore(path).verify(raw) is None


def test_revoke_unknown_returns_false(tmp_path):
    store = ApiKeyStore(tmp_path / "api_keys.json")
    assert store.revoke("nope") is False


def test_create_stores_scopes_and_rate_limit(tmp_path):
    store = ApiKeyStore(tmp_path / "api_keys.json")
    record, _ = store.create("scoped", models=["main-llm", " coding "], rate_limit_per_min=5)
    assert record["scopes"]["models"] == ["main-llm", "coding"]
    assert record["rate_limit_per_min"] == 5
    # Reloading preserves scopes.
    assert ApiKeyStore(tmp_path / "api_keys.json").list()[0]["scopes"]["models"] == ["main-llm", "coding"]


def test_tools_scope_semantics(tmp_path):
    store = ApiKeyStore(tmp_path / "api_keys.json")
    all_tools, _ = store.create("a", tools=None)
    no_tools, _ = store.create("b", tools=[])
    some_tools, _ = store.create("c", tools=["route_request", " load_skill "])
    assert all_tools["scopes"]["tools"] is None          # None = all
    assert no_tools["scopes"]["tools"] == []             # [] = none
    assert some_tools["scopes"]["tools"] == ["route_request", "load_skill"]
    # Persists across reload.
    reloaded = {k["label"]: k for k in ApiKeyStore(tmp_path / "api_keys.json").list()}
    assert reloaded["a"]["scopes"]["tools"] is None
    assert reloaded["b"]["scopes"]["tools"] == []


def test_wildcard_model_word_is_treated_as_unrestricted(tmp_path):
    store = ApiKeyStore(tmp_path / "api_keys.json")
    # Typing "all" (or "*"/"any") is a natural mistake for "no restriction" -- it must
    # not be taken as a literal (nonexistent) model name that locks the key out of
    # every real model.
    for word in ["all", "ALL", "*", "any"]:
        record, _ = store.create(f"key-{word}", models=[word])
        assert record["scopes"]["models"] == [], f"wildcard word {word!r} was not normalized"

    # Mixed with real names, the wildcard still wins (unambiguous "everything").
    mixed, _ = store.create("mixed", models=["main-llm", "all"])
    assert mixed["scopes"]["models"] == []

    # A real model name alone is untouched.
    real, _ = store.create("real", models=["main-llm"])
    assert real["scopes"]["models"] == ["main-llm"]
