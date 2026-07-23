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
