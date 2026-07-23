from services.orchestrator.llama_client import ProviderClients, resolve_base_url


def test_resolve_env_ref_uses_env(monkeypatch):
    monkeypatch.setenv("LLAMA_MAIN_URL", "http://llama-main:8080")
    assert resolve_base_url("${LLAMA_MAIN_URL}", "http://default:8080") == "http://llama-main:8080"


def test_resolve_env_ref_falls_back_when_unset(monkeypatch):
    monkeypatch.delenv("LLAMA_MAIN_URL", raising=False)
    # Unset env ref falls back to the shared default (the router), never breaking.
    assert resolve_base_url("${LLAMA_MAIN_URL}", "http://default:8080") == "http://default:8080"


def test_resolve_literal_and_empty():
    assert resolve_base_url("http://x:1234/v1", "http://default:8080") == "http://x:1234/v1"
    assert resolve_base_url("", "http://default:8080") == "http://default:8080"


def test_provider_clients_resolve_dedicated_urls(monkeypatch):
    monkeypatch.setenv("LLAMA_MAIN_URL", "http://llama-main:8080")
    monkeypatch.delenv("LLAMA_PROMPT_URL", raising=False)
    clients = ProviderClients(
        {
            "main": {"base_url": "${LLAMA_MAIN_URL}"},
            "prompt": {"base_url": "${LLAMA_PROMPT_URL}"},
        },
        timeout=1.0,
        default_base_url="http://router:8080",
    )
    assert clients.clients["main"].base_url == "http://llama-main:8080"
    # Prompt has no env set -> falls back to the shared router, so nothing breaks.
    assert clients.clients["prompt"].base_url == "http://router:8080"
